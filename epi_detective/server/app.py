"""
EpiDetective OpenEnv Server — uses the framework's create_app().

Provides:
  - WebSocket endpoint (/ws) for persistent sessions  ← OpenEnv validator connects here
  - HTTP endpoints (/reset, /step, /state, /health, /schema) with session state
  - Session management: pass session_id in requests, or use "default"
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

# Ensure package root is importable
_pkg_root = Path(__file__).parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from openenv.core.env_server.http_server import create_app
from models import EpiAction, EpiObservation
from server.epi_detective_environment import EpiDetectiveEnvironment

# ── Session store (shared across HTTP requests) ────────────────────────────────
_sessions: Dict[str, EpiDetectiveEnvironment] = {}


def _get_or_create_session(session_id: str) -> EpiDetectiveEnvironment:
    if session_id not in _sessions:
        _sessions[session_id] = EpiDetectiveEnvironment()
    return _sessions[session_id]


# ── Request / response models ─────────────────────────────────────────────────
class ResetRequest(BaseModel):
    task_id: str = "easy"
    seed: Optional[int] = None
    session_id: str = "default"


class StepRequest(BaseModel):
    command: str
    parameters: Dict[str, Any] = {}
    session_id: str = "default"


def _obs_to_dict(obs: EpiObservation) -> dict:
    return {
        "result_type": obs.result_type,
        "data": obs.data,
        "narrative": obs.narrative,
        "available_actions": obs.available_actions,
        "step_reward": obs.step_reward,
    }


# ── Base OpenEnv app (provides /ws WebSocket, /schema, /mcp) ──────────────────
_base_app = create_app(
    env=EpiDetectiveEnvironment,
    action_cls=EpiAction,
    observation_cls=EpiObservation,
    env_name="epi_detective",
)

# ── Main app — stateful HTTP routes defined first, then fallthrough to base ────
app = FastAPI(title="EpiDetective", version="1.0.0")

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>EpiDetective — Disease Outbreak Investigation</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 2rem; }
    .container { max-width: 860px; margin: 0 auto; }
    .hero { text-align: center; padding: 3rem 0 2rem; }
    .hero h1 { font-size: 2.8rem; font-weight: 800; color: #38bdf8; letter-spacing: -1px; }
    .hero .emoji { font-size: 3.5rem; display: block; margin-bottom: 1rem; }
    .hero p { font-size: 1.1rem; color: #94a3b8; margin-top: 0.75rem; max-width: 560px; margin-inline: auto; }
    .badge-row { display: flex; gap: 0.5rem; justify-content: center; flex-wrap: wrap; margin-top: 1.5rem; }
    .badge { background: #1e293b; border: 1px solid #334155; border-radius: 999px; padding: 0.3rem 0.9rem; font-size: 0.8rem; color: #7dd3fc; }
    .section { margin-top: 2.5rem; }
    .section h2 { font-size: 1.1rem; font-weight: 700; color: #7dd3fc; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 1rem; }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.25rem; }
    .card .method { display: inline-block; font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 4px; margin-bottom: 0.5rem; }
    .post { background: #166534; color: #86efac; }
    .get  { background: #1e3a5f; color: #7dd3fc; }
    .ws   { background: #581c87; color: #d8b4fe; }
    .card .path { font-family: monospace; font-size: 0.95rem; font-weight: 600; color: #f1f5f9; }
    .card .desc { font-size: 0.82rem; color: #94a3b8; margin-top: 0.4rem; }
    .task-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
    .task { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 1.25rem; text-align: center; }
    .task .label { font-size: 1.1rem; font-weight: 700; }
    .easy  { color: #4ade80; }
    .medium { color: #facc15; }
    .hard  { color: #f87171; }
    .task .steps { font-size: 0.8rem; color: #64748b; margin-top: 0.3rem; }
    .task .tdesc { font-size: 0.82rem; color: #94a3b8; margin-top: 0.5rem; }
    footer { text-align: center; margin-top: 3rem; color: #475569; font-size: 0.8rem; }
    a { color: #38bdf8; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
<div class="container">
  <div class="hero">
    <span class="emoji">🦠🔬</span>
    <h1>EpiDetective</h1>
    <p>An OpenEnv RL environment where AI agents play field epidemiologist — investigating disease outbreaks by gathering evidence and identifying the pathogen, source, and transmission route.</p>
    <div class="badge-row">
      <span class="badge">OpenEnv Compatible</span>
      <span class="badge">CDC 13-Step Protocol</span>
      <span class="badge">21 Pathogens</span>
      <span class="badge">Deterministic Grading</span>
      <span class="badge">WebSocket + HTTP</span>
    </div>
  </div>

  <div class="section">
    <h2>API Endpoints</h2>
    <div class="card-grid">
      <div class="card">
        <span class="method ws">WS</span>
        <div class="path">/ws</div>
        <div class="desc">WebSocket session — persistent state across reset/step cycles. Used by OpenEnv validator.</div>
      </div>
      <div class="card">
        <span class="method post">POST</span>
        <div class="path">/reset</div>
        <div class="desc">Start a new outbreak investigation.<br><code>task_id</code>, <code>seed</code>, <code>session_id</code></div>
      </div>
      <div class="card">
        <span class="method post">POST</span>
        <div class="path">/step</div>
        <div class="desc">Take one investigation action.<br><code>command</code>, <code>parameters</code>, <code>session_id</code></div>
      </div>
      <div class="card">
        <span class="method get">GET</span>
        <div class="path">/state</div>
        <div class="desc">Current episode state — episode ID and step count.</div>
      </div>
      <div class="card">
        <span class="method get">GET</span>
        <div class="path">/health</div>
        <div class="desc">Health check. Returns <code>{"status": "healthy"}</code>.</div>
      </div>
      <div class="card">
        <span class="method get">GET</span>
        <div class="path">/schema</div>
        <div class="desc">Full action and observation JSON schema.</div>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>Tasks</h2>
    <div class="task-grid">
      <div class="task">
        <div class="label easy">Easy</div>
        <div class="steps">Max 15 steps</div>
        <div class="tdesc">Single-source foodborne outbreak at a shared meal. Clear food signal, 30–80 attendees.</div>
      </div>
      <div class="task">
        <div class="label medium">Medium</div>
        <div class="steps">Max 25 steps</div>
        <div class="tdesc">Community-wide outbreak with seasonal illness noise. Subtler signal, 80–150 attendees.</div>
      </div>
      <div class="task">
        <div class="label hard">Hard</div>
        <div class="steps">Max 35 steps</div>
        <div class="tdesc">Two simultaneous overlapping outbreaks. Must separate clusters, 150–250 attendees.</div>
      </div>
    </div>
  </div>

  <footer>
    Built for the <strong>Meta PyTorch OpenEnv Hackathon 2026</strong> &nbsp;·&nbsp;
    <a href="/schema">Schema</a> &nbsp;·&nbsp;
    <a href="/health">Health</a> &nbsp;·&nbsp;
    <a href="/docs">Docs</a>
  </footer>
</div>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=_HTML)


@app.post("/reset")
async def reset(req: ResetRequest):
    env = _get_or_create_session(req.session_id)
    obs = env.reset(seed=req.seed, task_id=req.task_id)
    return JSONResponse({
        "observation": _obs_to_dict(obs),
        "reward": 0.0,
        "done": False,
        "session_id": req.session_id,
    })


@app.post("/step")
async def step(req: StepRequest):
    env = _sessions.get(req.session_id)
    if env is None:
        raise HTTPException(status_code=400, detail=f"No active session '{req.session_id}'. Call /reset first.")
    action = EpiAction(command=req.command, parameters=req.parameters)
    obs = env.step(action)
    return JSONResponse({
        "observation": _obs_to_dict(obs),
        "reward": obs.reward,
        "done": obs.done,
        "session_id": req.session_id,
    })


@app.get("/state")
async def state(session_id: str = "default"):
    env = _sessions.get(session_id)
    if env is None:
        return JSONResponse({"episode_id": None, "step_count": 0, "session_id": session_id})
    s = env.state
    return JSONResponse({"episode_id": s.episode_id, "step_count": s.step_count, "session_id": session_id})


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Mount base app at "/" so its /ws WebSocket is reachable at /ws
# (our explicit routes above take priority over the mount)
app.mount("/", _base_app)


def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
