"""
EpiDetective OpenEnv Server — uses the framework's create_app().

Provides:
  - WebSocket endpoint (/ws) for persistent sessions
  - HTTP endpoints (/reset, /step, /state, /health, /schema) with session state
  - Session management: pass session_id in requests, or use "default"
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
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


# ── Base OpenEnv app (provides /ws, /health, /schema, /mcp) ───────────────────
_base_app = create_app(
    env=EpiDetectiveEnvironment,
    action_cls=EpiAction,
    observation_cls=EpiObservation,
    env_name="epi_detective",
)

# ── Main app that mounts stateful HTTP routes ─────────────────────────────────
app = FastAPI(title="EpiDetective", version="1.0.0")


@app.get("/")
async def root():
    return {
        "name": "EpiDetective",
        "description": "Disease outbreak investigation RL environment",
        "endpoints": {
            "POST /reset": "Start a new investigation (params: task_id, seed, session_id)",
            "POST /step": "Take an investigation action (params: command, parameters, session_id)",
            "GET  /state": "Get current episode state (params: session_id)",
            "GET  /health": "Health check",
            "GET  /schema": "Action/observation schema",
        },
        "tasks": ["easy", "medium", "hard"],
    }


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


# Mount WebSocket + schema/mcp endpoints from the framework app
app.mount("/ws", _base_app)


def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
