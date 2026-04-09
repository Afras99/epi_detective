# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
EpiDetective OpenEnv Environment Server.

FastAPI server implementing the OpenEnv spec: POST /reset, POST /step, GET /state,
GET /schema, GET /health.

Agents investigate disease outbreaks by issuing investigation commands and
receiving evidence observations. Scenarios are seeded and fully deterministic.

Usage:
    # Development (auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 7860

    # Via entry point:
    uv run --project . server
    uv run --project . server --port 7860
"""

import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Make engine/ and grader/ importable when running from the package root
_pkg_root = Path(__file__).parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from engine.scenario_generator import ScenarioGenerator
from engine.evidence_engine import EvidenceEngine
from grader.grader import EpiGrader, compute_step_reward

app = FastAPI(
    title="EpiDetective",
    description="""
## Disease Outbreak Investigation Environment

An AI agent plays the role of a field epidemiologist responding to a disease outbreak.
The agent must gather evidence systematically and identify the **pathogen**, **food source**, and **transmission route**.

### How to use
1. `POST /reset` — start a new investigation (choose easy / medium / hard)
2. `POST /step` — take one investigation action (repeat until done)
3. `POST /step` with `submit_final_answer` — submit your conclusion and get a score (0.0 – 1.0)

### Available investigation commands
| Command | What it returns |
|---|---|
| `view_initial_alert` | The original outbreak notification |
| `request_line_list` | All ill patients: age, sex, onset time, symptoms |
| `generate_epi_curve` | Cases plotted by hour — reveals point-source vs propagated |
| `request_lab_results` | Pathogen identified per patient |
| `get_exposure_history` | What each patient ate at the event |
| `calculate_attack_rate` | Ate-ill vs ate-well 2×2 table + relative risk |
| `calculate_odds_ratio` | Odds ratio for food-illness association |
| `request_environmental_samples` | Environmental swab results from venue |
| `submit_hypothesis` | Partial feedback on your theory (no reward) |
| `submit_final_answer` | **Ends the episode** — triggers grader, returns final score |

### Scoring (on submit_final_answer)
- Pathogen identified correctly → **25%**
- Food source identified correctly → **25%**
- Transmission route correct → **20%**
- Case definition quality → **15%**
- Step efficiency → **15%**
""",
    version="0.1.0",
    contact={"name": "Afras", "email": "afrasplacement@gmail.com"},
    license_info={"name": "MIT"},
)

# ── Request / Response models ─────────────────────────────────────────────────

class ActionRequest(BaseModel):
    command: str = Field(
        default="request_line_list",
        description="Investigation command to execute. One of: view_initial_alert, request_line_list, generate_epi_curve, request_lab_results, get_exposure_history, calculate_attack_rate, calculate_odds_ratio, request_environmental_samples, submit_hypothesis, submit_final_answer",
        examples=["request_line_list", "submit_final_answer"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier returned by /reset. Uses default session if not provided.",
    )
    parameters: Dict[str, Any] = Field(
        default={},
        description="""Command-specific parameters:
- `request_line_list` → `{}`
- `generate_epi_curve` → `{"grouping": "hour"}`
- `request_lab_results` → `{"case_ids": ["c001", "c002"]}` (empty = first 10)
- `get_exposure_history` → `{"case_ids": ["c001"]}` (empty = first 15 ill)
- `calculate_attack_rate` → `{"food_item": "chicken"}`
- `calculate_odds_ratio` → `{"exposure": "potato_salad"}`
- `request_environmental_samples` → `{"location": "kitchen"}`
- `submit_hypothesis` → `{"pathogen": "salmonella", "source": "chicken", "route": "foodborne"}`
- `submit_final_answer` → `{"pathogen": "salmonella", "source": "chicken", "route": "foodborne", "case_definition": {"clinical": "diarrhea", "time": "6-72h after meal", "place": "restaurant"}}`
""",
        examples=[
            {},
            {"case_ids": ["c001", "c002"]},
            {"food_item": "chicken"},
            {"pathogen": "salmonella", "source": "chicken", "route": "foodborne",
             "case_definition": {"clinical": "diarrhea and fever", "time": "6-72h after meal", "place": "event venue"}},
        ],
    )

class ResetRequest(BaseModel):
    task_id: str = Field(
        default="easy",
        description="Difficulty level of the outbreak investigation",
        examples=["easy", "medium", "hard"],
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility. Same seed always produces the same outbreak scenario. Leave empty for a random scenario.",
        examples=[42, 99, 1234],
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for concurrent use. Auto-generated if not provided.",
    )

class StepResponse(BaseModel):
    observation: Dict[str, Any] = Field(description="What the agent observes: narrative text, structured data, available actions, step reward")
    reward: float = Field(description="Reward for this step. Per-step: 0.02–0.08. Final score: 0.0–1.0 on submit_final_answer")
    done: bool = Field(description="True when the episode is complete (after submit_final_answer or step budget exhausted)")
    state: Dict[str, Any] = Field(description="Current session state: step_count, steps_remaining, evidence_unlocked, task_id")

# ── Available commands ────────────────────────────────────────────────────────

AVAILABLE_ACTIONS: List[str] = [
    "view_initial_alert",
    "request_line_list",
    "generate_epi_curve",
    "request_lab_results",
    "get_exposure_history",
    "calculate_attack_rate",
    "calculate_odds_ratio",
    "request_environmental_samples",
    "submit_hypothesis",
    "submit_final_answer",
]

# ── Session state ─────────────────────────────────────────────────────────────

import uuid

generator = ScenarioGenerator()
grader = EpiGrader()


class SessionState:
    def __init__(self):
        self.scenario = None
        self.evidence_engine = None
        self.step_count = 0
        self.action_history: set = set()
        self.is_done = False
        self.total_reward = 0.0


sessions: Dict[str, SessionState] = {}


def _get_or_create_session(session_id: str) -> SessionState:
    if session_id not in sessions:
        sessions[session_id] = SessionState()
    return sessions[session_id]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_state(sess: SessionState) -> Dict[str, Any]:
    return {
        "step_count": sess.step_count,
        "is_done": sess.is_done,
        "total_reward": round(sess.total_reward, 4),
        "task_id": sess.scenario.task_id if sess.scenario else None,
        "steps_remaining": (sess.scenario.max_steps - sess.step_count) if sess.scenario else 0,
        "evidence_unlocked": list(sess.evidence_engine.unlocked) if sess.evidence_engine else [],
        "actions_taken": len(sess.action_history),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, summary="Landing page", description="Interactive landing page with environment overview, task descriptions, and links to API docs.", include_in_schema=False)
def root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>EpiDetective</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f1117; color: #e2e8f0; min-height: 100vh; }
    .realworld { background: #161b27; border: 1px solid #2d3748; border-left: 4px solid #48bb78;
                 border-radius: 8px; padding: 20px 24px; margin-bottom: 40px; }
    .realworld h3 { color: #68d391; font-size: 14px; font-weight: 700;
                    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .realworld p { color: #a0aec0; font-size: 14px; line-height: 1.7; }
    .realworld strong { color: #e2e8f0; }
    .steps { counter-reset: step; margin-bottom: 40px; }
    .step-item { display: flex; gap: 16px; margin-bottom: 16px; align-items: flex-start; }
    .step-num { background: #1a3a2a; color: #48bb78; border: 1px solid #276749;
                border-radius: 50%; width: 32px; height: 32px; flex-shrink: 0;
                display: flex; align-items: center; justify-content: center;
                font-weight: 700; font-size: 13px; }
    .step-text h4 { color: #e2e8f0; font-size: 14px; margin-bottom: 4px; }
    .step-text p { color: #718096; font-size: 13px; }
    .hero { background: linear-gradient(135deg, #1a1f2e 0%, #162032 100%);
            border-bottom: 1px solid #2d3748; padding: 60px 40px; text-align: center; }
    .badge { display: inline-block; background: #22543d; color: #68d391;
             padding: 4px 14px; border-radius: 20px; font-size: 13px;
             font-weight: 600; margin-bottom: 20px; }
    h1 { font-size: 48px; font-weight: 800; color: #fff; margin-bottom: 12px; }
    h1 span { color: #48bb78; }
    .subtitle { font-size: 18px; color: #a0aec0; max-width: 600px;
                margin: 0 auto 32px; line-height: 1.6; }
    .status { display: inline-flex; align-items: center; gap: 8px;
              background: #1a2744; border: 1px solid #2d3748;
              padding: 8px 20px; border-radius: 30px; font-size: 14px; }
    .dot { width: 8px; height: 8px; background: #48bb78;
           border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
    .container { max-width: 1000px; margin: 0 auto; padding: 50px 40px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 50px; }
    .card { background: #1a1f2e; border: 1px solid #2d3748; border-radius: 12px;
            padding: 28px; transition: border-color 0.2s; }
    .card:hover { border-color: #48bb78; }
    .card-icon { font-size: 32px; margin-bottom: 14px; }
    .card h3 { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 8px; }
    .card p { font-size: 14px; color: #718096; line-height: 1.6; }
    .card .tag { display: inline-block; margin-top: 12px; padding: 3px 10px;
                 border-radius: 12px; font-size: 12px; font-weight: 600; }
    .easy { background: #1c4532; color: #68d391; }
    .medium { background: #744210; color: #f6ad55; }
    .hard { background: #63171b; color: #fc8181; }
    h2 { font-size: 22px; font-weight: 700; color: #fff;
         margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #2d3748; }
    .endpoints { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 50px; }
    .ep { background: #1a1f2e; border: 1px solid #2d3748; border-radius: 10px;
          padding: 16px 20px; display: flex; align-items: center; gap: 14px; }
    .method { font-size: 11px; font-weight: 800; padding: 3px 10px;
              border-radius: 6px; min-width: 44px; text-align: center; }
    .post { background: #1a3a1a; color: #68d391; }
    .get  { background: #1a2744; color: #63b3ed; }
    .ep-path { font-family: monospace; font-size: 15px; color: #e2e8f0; font-weight: 600; }
    .ep-desc { font-size: 13px; color: #718096; margin-top: 2px; }
    .cta { text-align: center; margin-top: 20px; }
    .btn { display: inline-block; background: #48bb78; color: #0f1117;
           padding: 14px 36px; border-radius: 8px; font-weight: 700;
           font-size: 16px; text-decoration: none; margin: 8px;
           transition: background 0.2s; }
    .btn:hover { background: #68d391; }
    .btn-outline { background: transparent; color: #48bb78;
                   border: 2px solid #48bb78; }
    .btn-outline:hover { background: #48bb78; color: #0f1117; }
    footer { text-align: center; padding: 30px; color: #4a5568;
             font-size: 13px; border-top: 1px solid #2d3748; }
  </style>
</head>
<body>
  <div class="hero">
    <div class="badge">🔬 OpenEnv Environment</div>
    <h1>Epi<span>Detective</span></h1>
    <p class="subtitle">
      A real-world reinforcement learning environment where AI agents investigate
      disease outbreaks — gathering evidence, running statistics, and identifying
      pathogens, sources, and transmission routes.
    </p>
    <div class="status">
      <div class="dot"></div>
      <span>Server running · 21 pathogens · 15 food vehicles · 3 tasks</span>
    </div>
  </div>

  <div class="container">

    <div class="realworld">
      <h3>🏥 Real-World Professional Workflow</h3>
      <p>
        EpiDetective directly models the <strong>CDC's canonical 13-step outbreak investigation protocol</strong> —
        the same methodology used by epidemiologists at CDC, WHO, and state health departments to investigate
        <strong>thousands of foodborne illness clusters every year</strong>. Every action in this environment
        corresponds to something a real public health investigator actually does in the field.
        <br><br>
        Pathogen profiles, incubation periods, and food–pathogen associations are drawn from
        <strong>CDC NORS outbreak records (1998–2022)</strong>, the <strong>FDA Bad Bug Book</strong>, and
        peer-reviewed literature. This is not a game — an agent that solves this environment is learning
        skills directly applicable to automated outbreak surveillance.
      </p>
    </div>

    <h2>Investigation Workflow</h2>
    <div class="steps">
      <div class="step-item"><div class="step-num">1</div><div class="step-text"><h4>view_initial_alert</h4><p>Read the outbreak notification from the health department</p></div></div>
      <div class="step-item"><div class="step-num">2</div><div class="step-text"><h4>request_line_list</h4><p>Get all ill patients — demographics, onset times, symptoms, hospitalizations</p></div></div>
      <div class="step-item"><div class="step-num">3</div><div class="step-text"><h4>request_lab_results</h4><p>Identify the pathogen from clinical specimens (+0.08 reward)</p></div></div>
      <div class="step-item"><div class="step-num">4</div><div class="step-text"><h4>get_exposure_history</h4><p>Find out what each patient ate or where they went</p></div></div>
      <div class="step-item"><div class="step-num">5</div><div class="step-text"><h4>calculate_attack_rate</h4><p>Run 2×2 tables to find which food has the highest relative risk</p></div></div>
      <div class="step-item"><div class="step-num">6</div><div class="step-text"><h4>submit_final_answer</h4><p>Submit pathogen + source + route + case definition → receive final score (0.0–1.0)</p></div></div>
    </div>

    <h2>Tasks</h2>
    <div class="grid">
      <div class="card">
        <div class="card-icon">🍽️</div>
        <h3>Point-Source Outbreak</h3>
        <p>Single contaminated food at a shared meal. Identify the pathogen and guilty food before the step budget runs out.</p>
        <span class="tag easy">Easy · 15 steps</span>
      </div>
      <div class="card">
        <div class="card-icon">🌬️</div>
        <h3>Community Respiratory</h3>
        <p>Legionella cluster with concurrent influenza noise. Separate signal from background illness activity.</p>
        <span class="tag medium">Medium · 25 steps</span>
      </div>
      <div class="card">
        <div class="card-icon">🔀</div>
        <h3>Overlapping Outbreaks</h3>
        <p>Two simultaneous outbreaks from different pathogens. Discover both and report each independently.</p>
        <span class="tag hard">Hard · 35 steps</span>
      </div>
    </div>

    <h2>API Endpoints</h2>
    <div class="endpoints">
      <div class="ep">
        <div>
          <div class="method post">POST</div>
        </div>
        <div>
          <div class="ep-path">/reset</div>
          <div class="ep-desc">Start a new outbreak investigation</div>
        </div>
      </div>
      <div class="ep">
        <div>
          <div class="method post">POST</div>
        </div>
        <div>
          <div class="ep-path">/step</div>
          <div class="ep-desc">Take one investigation action</div>
        </div>
      </div>
      <div class="ep">
        <div>
          <div class="method get">GET</div>
        </div>
        <div>
          <div class="ep-path">/state</div>
          <div class="ep-desc">Check current session progress</div>
        </div>
      </div>
      <div class="ep">
        <div>
          <div class="method get">GET</div>
        </div>
        <div>
          <div class="ep-path">/health</div>
          <div class="ep-desc">Server health check</div>
        </div>
      </div>
      <div class="ep">
        <div>
          <div class="method get">GET</div>
        </div>
        <div>
          <div class="ep-path">/schema</div>
          <div class="ep-desc">Action and observation schema</div>
        </div>
      </div>
      <div class="ep">
        <div>
          <div class="method get">GET</div>
        </div>
        <div>
          <div class="ep-path">/docs</div>
          <div class="ep-desc">Interactive API documentation</div>
        </div>
      </div>
    </div>

    <div class="cta">
      <a href="/docs" class="btn">📖 Interactive API Docs</a>
      <a href="/health" class="btn btn-outline">⚡ Health Check</a>
    </div>
  </div>

  <footer>
    EpiDetective · Built for the Meta × PyTorch × Hugging Face OpenEnv Hackathon · by Afras
  </footer>
</body>
</html>"""


@app.get("/health", summary="Health check", description="Returns server status. Used by the hackathon validator to confirm the space is running.")
def health():
    return {"status": "healthy"}


@app.get("/schema")
def schema():
    return {
        "action": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "enum": AVAILABLE_ACTIONS},
                "parameters": {"type": "object"},
            },
        },
        "observation": {
            "type": "object",
            "properties": {
                "result_type": {"type": "string"},
                "data": {"type": "object"},
                "narrative": {"type": "string"},
                "available_actions": {"type": "array", "items": {"type": "string"}},
                "step_reward": {"type": "number"},
                "done": {"type": "boolean"},
            },
        },
    }


@app.post(
    "/reset",
    summary="Start a new investigation",
    description="""Generates a fresh outbreak scenario and returns the initial alert narrative.

**Always call this first** before any `/step` calls.

The scenario is fully seeded — passing the same `seed` and `task_id` always produces the identical outbreak, which makes scoring reproducible.

Returns the initial alert text describing the outbreak, available investigation commands, and session state.""",
)
def reset(req: ResetRequest = ResetRequest()):
    session_id = req.session_id or "default"
    sess = _get_or_create_session(session_id)

    seed = req.seed if req.seed is not None else random.randint(0, 2**31)
    sess.scenario = generator.generate(req.task_id, seed)
    sess.evidence_engine = EvidenceEngine(sess.scenario)
    sess.step_count = 0
    sess.action_history = set()
    sess.is_done = False
    sess.total_reward = 0.0

    observation = {
        "result_type": "alert",
        "data": {"task_id": req.task_id, "seed": seed, "session_id": session_id},
        "narrative": sess.scenario.initial_alert,
        "available_actions": AVAILABLE_ACTIONS,
        "step_reward": 0.0,
        "done": False,
    }

    return StepResponse(
        observation=observation,
        reward=0.0,
        done=False,
        state=_get_state(sess),
    )


@app.post(
    "/step",
    summary="Take one investigation action",
    description="""Executes one investigation command and returns an observation.

**Call `/reset` first** to start a scenario before calling this.

Each command gathers different evidence. The agent must choose wisely — repeating the same action costs −0.02 reward, and the step budget is limited.

**Recommended investigation order:**
1. `request_line_list` — see who got sick and when (incubation clues)
2. `request_lab_results` — identify the pathogen from lab tests
3. `get_exposure_history` — see what patients ate
4. `calculate_attack_rate` — find the guilty food statistically
5. `submit_final_answer` — submit conclusion and receive final score (0.0–1.0)

Use `submit_hypothesis` at any point to get partial feedback without ending the episode.""",
)
def step(action: ActionRequest):
    session_id = action.session_id or "default"
    sess = _get_or_create_session(session_id)

    if sess.scenario is None:
        return StepResponse(
            observation={
                "result_type": "error",
                "narrative": "No active investigation. Call POST /reset with task_id='easy', 'medium', or 'hard' to start.",
                "data": {},
                "available_actions": ["reset"],
                "step_reward": 0.0,
                "done": False,
            },
            reward=0.0,
            done=False,
            state=_get_state(sess),
        )

    if sess.is_done:
        return StepResponse(
            observation={
                "result_type": "error",
                "narrative": "Investigation complete. Call POST /reset to start a new case.",
                "data": {},
                "available_actions": [],
                "done": True,
            },
            reward=0.0,
            done=True,
            state=_get_state(sess),
        )

    sess.step_count += 1
    command = action.command
    params = action.parameters

    # ── Final submission ───────────────────────────────────────────────────────
    if command == "submit_final_answer":
        final_score = grader.grade(
            params,
            sess.scenario.ground_truth,
            sess.step_count,
            sess.scenario.optimal_steps,
            sess.scenario.max_steps,
        )
        sess.is_done = True
        sess.total_reward = final_score

        return StepResponse(
            observation={
                "result_type": "final_score",
                "data": {"score": final_score, "steps_taken": sess.step_count},
                "narrative": (
                    f"Investigation complete. Final score: {final_score:.4f} / 1.0 "
                    f"({sess.step_count} steps taken)."
                ),
                "available_actions": [],
                "step_reward": final_score,
                "done": True,
            },
            reward=final_score,
            done=True,
            state=_get_state(sess),
        )

    # ── Regular investigation actions ──────────────────────────────────────────
    obs_data = sess.evidence_engine.process_action(command, params)

    step_reward = compute_step_reward(
        command, params, sess.action_history,
        sess.scenario.ground_truth,
        sess.step_count, sess.scenario.optimal_steps, sess.scenario.max_steps,
    )
    sess.action_history.add(f"{command}:{json.dumps(params, sort_keys=True)}")
    sess.total_reward += step_reward

    remaining = sess.scenario.max_steps - sess.step_count
    if remaining <= 0:
        obs_data["narrative"] += "\n\n⚠️ Step budget exhausted! You must submit your final answer now."
        obs_data["available_actions"] = ["submit_final_answer"]
    else:
        obs_data["available_actions"] = AVAILABLE_ACTIONS

    obs_data["step_reward"] = step_reward
    obs_data["done"] = False

    return StepResponse(
        observation=obs_data,
        reward=step_reward,
        done=False,
        state=_get_state(sess),
    )


@app.get("/state", summary="Get current session state", description="Returns current investigation progress: step count, steps remaining, evidence unlocked so far, and whether the episode is complete. Does not consume a step.")
def state():
    sess = _get_or_create_session("default")
    return _get_state(sess)


# ── Entry point ───────────────────────────────────────────────────────────────

def main(host: str = "0.0.0.0", port: int = 7860):
    """Run the server directly via `uv run --project . server` or `python -m server.app`."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
