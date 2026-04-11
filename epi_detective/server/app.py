"""
EpiDetective OpenEnv Server.

Architecture:
  - Pure create_app() provides WebSocket /ws (used by OpenEnv validator)
    and GET /health, GET /schema.
  - Stateful HTTP session store layered on top for /reset, /step, /state
    so inference.py agents can use plain HTTP with persistent state.

HTTP /step format: {"action": {"command": "...", "parameters": {...}}}
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ValidationError

_pkg_root = Path(__file__).parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from openenv.core.env_server.http_server import create_app
from models import EpiAction, EpiObservation
from server.epi_detective_environment import EpiDetectiveEnvironment

# ── In-memory session store ────────────────────────────────────────────────────
_sessions: Dict[str, EpiDetectiveEnvironment] = {}


def _get_or_create_session(session_id: str) -> EpiDetectiveEnvironment:
    if session_id not in _sessions:
        _sessions[session_id] = EpiDetectiveEnvironment()
    return _sessions[session_id]


# ── Request models ─────────────────────────────────────────────────────────────
class ResetRequest(BaseModel):
    task_id: str = "easy"
    seed: Optional[int] = None
    session_id: str = "default"


class ActionPayload(BaseModel):
    command: str
    parameters: Dict[str, Any] = {}


class StepRequest(BaseModel):
    action: ActionPayload
    session_id: str = "default"


def _obs_to_dict(obs: EpiObservation) -> dict:
    return {
        "result_type": obs.result_type,
        "data": obs.data,
        "narrative": obs.narrative,
        "available_actions": obs.available_actions,
        "step_reward": obs.step_reward,
    }


# ── Framework app (WebSocket /ws, GET /health, GET /schema) ───────────────────
_framework_app = create_app(
    env=EpiDetectiveEnvironment,
    action_cls=EpiAction,
    observation_cls=EpiObservation,
    env_name="epi_detective",
)

# ── Main app — stateful routes + HTML landing page ────────────────────────────
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>EpiDetective — Disease Outbreak Investigation</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;padding:2rem}
    .container{max-width:860px;margin:0 auto}
    .hero{text-align:center;padding:3rem 0 2rem}
    .hero h1{font-size:2.8rem;font-weight:800;color:#38bdf8;letter-spacing:-1px}
    .hero .emoji{font-size:3.5rem;display:block;margin-bottom:1rem}
    .hero p{font-size:1.1rem;color:#94a3b8;margin-top:.75rem;max-width:560px;margin-inline:auto}
    .badge-row{display:flex;gap:.5rem;justify-content:center;flex-wrap:wrap;margin-top:1.5rem}
    .badge{background:#1e293b;border:1px solid #334155;border-radius:999px;padding:.3rem .9rem;font-size:.8rem;color:#7dd3fc}
    .section{margin-top:2.5rem}
    .section h2{font-size:1.1rem;font-weight:700;color:#7dd3fc;text-transform:uppercase;letter-spacing:1px;margin-bottom:1rem}
    .card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}
    .card{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:1.25rem}
    .card .method{display:inline-block;font-size:.7rem;font-weight:700;padding:.15rem .5rem;border-radius:4px;margin-bottom:.5rem}
    .post{background:#166534;color:#86efac}.get{background:#1e3a5f;color:#7dd3fc}.ws{background:#581c87;color:#d8b4fe}
    .card .path{font-family:monospace;font-size:.95rem;font-weight:600;color:#f1f5f9}
    .card .desc{font-size:.82rem;color:#94a3b8;margin-top:.4rem}
    .task-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}
    .task{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:1.25rem;text-align:center}
    .task .label{font-size:1.1rem;font-weight:700}
    .easy{color:#4ade80}.medium{color:#facc15}.hard{color:#f87171}
    .task .steps{font-size:.8rem;color:#64748b;margin-top:.3rem}
    .task .tdesc{font-size:.82rem;color:#94a3b8;margin-top:.5rem}
    footer{text-align:center;margin-top:3rem;color:#475569;font-size:.8rem}
    a{color:#38bdf8;text-decoration:none}a:hover{text-decoration:underline}
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
      <div class="card"><span class="method ws">WS</span><div class="path">/ws</div><div class="desc">WebSocket — persistent session used by OpenEnv validator.</div></div>
      <div class="card"><span class="method post">POST</span><div class="path">/reset</div><div class="desc">Start new investigation.<br><code>{"task_id":"easy","seed":42}</code></div></div>
      <div class="card"><span class="method post">POST</span><div class="path">/step</div><div class="desc">Take one action.<br><code>{"action":{"command":"...","parameters":{}}}</code></div></div>
      <div class="card"><span class="method get">GET</span><div class="path">/state</div><div class="desc">Current episode state.</div></div>
      <div class="card"><span class="method get">GET</span><div class="path">/health</div><div class="desc">Health check.</div></div>
      <div class="card"><span class="method get">GET</span><div class="path">/schema</div><div class="desc">Action &amp; observation JSON schema.</div></div>
    </div>
  </div>
  <div class="section">
    <h2>Tasks</h2>
    <div class="task-grid">
      <div class="task"><div class="label easy">Easy</div><div class="steps">Max 15 steps</div><div class="tdesc">Single-source foodborne outbreak. Clear food signal, 30–80 attendees.</div></div>
      <div class="task"><div class="label medium">Medium</div><div class="steps">Max 25 steps</div><div class="tdesc">Community outbreak with noise. Subtler signal, 80–150 attendees.</div></div>
      <div class="task"><div class="label hard">Hard</div><div class="steps">Max 35 steps</div><div class="tdesc">Two overlapping outbreaks. Must separate clusters, 150–250 attendees.</div></div>
    </div>
  </div>
  <footer>Built for the <strong>Meta PyTorch OpenEnv Hackathon 2026</strong> &nbsp;·&nbsp; <a href="/schema">Schema</a> &nbsp;·&nbsp; <a href="/health">Health</a> &nbsp;·&nbsp; <a href="/docs">Docs</a></footer>
</div>
</body>
</html>"""

app = FastAPI(title="EpiDetective", version="1.0.0")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return HTMLResponse(content=_HTML)


@app.post("/reset")
async def reset(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        req = ResetRequest(**body)
    except (ValidationError, TypeError):
        req = ResetRequest()
    env = _get_or_create_session(req.session_id)
    obs = env.reset(seed=req.seed, task_id=req.task_id)
    return JSONResponse({
        "observation": _obs_to_dict(obs),
        "reward": 0.0,
        "done": False,
        "session_id": req.session_id,
    })


@app.post("/step")
async def step(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        req = StepRequest(**body)
    except (ValidationError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    env = _sessions.get(req.session_id)
    if env is None:
        raise HTTPException(
            status_code=400,
            detail=f"No active session '{req.session_id}'. Call /reset first.",
        )
    action = EpiAction(command=req.action.command, parameters=req.action.parameters)
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


# Mount framework app at "/" — its /ws WebSocket is reachable at /ws,
# its /schema is reachable at /schema. Our explicit routes above take priority.
app.mount("/", _framework_app)


def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
