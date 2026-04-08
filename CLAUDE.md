# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Epi Detective** is an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) environment — a reinforcement-learning-style environment exposed over HTTP/WebSocket. It currently implements a simple echo environment as a scaffold for building more complex RL environments.

The project has two halves:
- **Server** (`epi_detective/server/`): A FastAPI app wrapping `EpiDetectiveEnvironment`, served via `openenv-core`'s `create_app` factory.
- **Client** (`epi_detective/client.py`): A typed `EnvClient` subclass that connects to the server over WebSocket.

## Commands

All commands run from the `epi_detective/` directory (where `pyproject.toml` lives).

```bash
# Install dependencies
uv sync

# Run the server (development, with auto-reload)
uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

# Run the server via entry point
uv run --project . server
uv run --project . server --port 8001

# Run tests
uv run pytest

# Run a single test
uv run pytest path/to/test_file.py::test_name
```

## Architecture

### Key files

| File | Role |
|---|---|
| `epi_detective/models.py` | Pydantic `Action` / `Observation` types (`EpiDetectiveAction`, `EpiDetectiveObservation`) |
| `epi_detective/server/epi_detective_environment.py` | Core environment logic — implements `reset()` and `step()` |
| `epi_detective/server/app.py` | FastAPI app created via `openenv-core`'s `create_app`; exposes REST + WebSocket endpoints |
| `epi_detective/client.py` | `EpiDetectiveEnv` client — connects over WebSocket, serializes actions, parses observations |
| `epi_detective/openenv.yaml` | OpenEnv manifest (`spec_version`, runtime, port) |

### OpenEnv conventions

- `EpiDetectiveEnvironment` extends `openenv.core.env_server.interfaces.Environment` and must implement `reset() -> Observation` and `step(action) -> Observation`.
- `create_app(EnvClass, ActionClass, ObservationClass, ...)` wires up the standard endpoints: `POST /reset`, `POST /step`, `GET /state`, `GET /schema`, `WS /ws`.
- `EpiDetectiveEnv` (client) extends `EnvClient[Action, Observation, State]` and must implement `_step_payload()` and `_parse_result()`.
- `SUPPORTS_CONCURRENT_SESSIONS = True` on the environment class allows multiple WebSocket sessions; `max_concurrent_envs` in `create_app` caps concurrent sessions server-side.

### Extending the environment

To build a real environment on top of this scaffold:
1. Update `models.py` — add fields to `EpiDetectiveAction` and `EpiDetectiveObservation`.
2. Update `server/epi_detective_environment.py` — implement real `reset()` / `step()` logic.
3. Update `client.py` — update `_step_payload()` to serialize new action fields and `_parse_result()` to parse new observation fields.
4. Add environment-specific pip dependencies to `pyproject.toml` under `[project] dependencies`.
