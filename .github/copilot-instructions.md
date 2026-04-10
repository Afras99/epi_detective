# Copilot Instructions

## Project Overview

EpiDetective is an OpenEnv RL environment where AI agents investigate disease outbreaks. Agents gather epidemiological evidence (line lists, lab results, epi curves, exposure histories) to identify a pathogen, contamination source, and transmission route. Scenarios are procedurally generated with planted ground truth, enabling deterministic grading.

## Repository Layout

```
epi_detective/          ← deployable OpenEnv package (everything to ship lives here)
  Dockerfile            ← python:3.11-slim, port 7860
  inference.py          ← LLM agent entry point (hackathon requirement: must be at package root)
  openenv.yaml          ← OpenEnv spec: 3 tasks (easy/medium/hard), port 7860
  requirements.txt      ← 5 deps: fastapi, uvicorn, pydantic, openai, requests
  models.py             ← Pydantic EpiAction / EpiObservation
  client.py             ← HTTP client wrapper (EpiDetectiveClient)
  server/app.py         ← FastAPI app: POST /reset, POST /step, GET /state, GET /schema, GET /health
  engine/               ← ScenarioGenerator + EvidenceEngine
  grader/               ← EpiGrader (final score) + compute_step_reward (dense rewards)
  data/                 ← pathogens.json, food_vehicles.json, settings.json
sprint/                 ← original prototype (identical logic, kept for reference)
engine/, grader/, data/ ← repo-root copies (identical to epi_detective/engine|grader|data)
```

The `epi_detective/` package is self-contained and is what gets deployed via Docker / `openenv push`.

## Build & Run Commands

All commands run from `epi_detective/` (the deployable package directory):

```bash
# Install dependencies
pip install -r requirements.txt
# or with uv:
cd epi_detective && uv sync

# Start server (development, auto-reload)
uvicorn server.app:app --reload --host 0.0.0.0 --port 7860

# Via uv entry point
uv run --project . server
uv run --project . server --port 7861

# Run the LLM agent
export API_BASE_URL="https://api-inference.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export HF_TOKEN="hf_..."
export ENV_URL="http://localhost:7860"
python inference.py

# Run tests
uv run pytest

# Run a single test
uv run pytest path/to/test_file.py::test_name
```

## Architecture: How a Game Runs

1. **`POST /reset`** — `ScenarioGenerator.generate(task_id, seed)` creates a `Scenario` with planted ground truth (pathogen, source, route, case data). Returns initial outbreak alert narrative.
2. **`POST /step`** — Agent sends `{command, parameters}`. `EvidenceEngine.process_action()` gates information behind the command; `compute_step_reward()` returns a dense reward. Repeat up to `max_steps`.
3. **`submit_final_answer`** — `EpiGrader.grade()` scores against planted ground truth → returns 0.0–1.0.

`server/app.py` uses **global module-level state** (single active session). This is intentional for HF Spaces single-user deployment. The server also exposes `GET /state` and `GET /schema` for OpenEnv spec compliance.

## Agent Action Protocol

Every step POSTs `{"command": "<action>", "parameters": {...}}`. Available commands:

| Command | Key parameter(s) |
|---|---|
| `view_initial_alert` | — |
| `request_line_list` | — |
| `generate_epi_curve` | `grouping: "hour"` |
| `request_lab_results` | `case_ids: ["c001", ...]` |
| `get_exposure_history` | `case_ids: ["c001", ...]` |
| `calculate_attack_rate` | `food_item: "potato_salad"` |
| `calculate_odds_ratio` | `exposure: "chicken"` |
| `request_environmental_samples` | `location: "kitchen"` |
| `submit_hypothesis` | `pathogen, source, route` |
| `submit_final_answer` | `pathogen, source, route, case_definition: {clinical, time, place}` |

Repeat actions return `is_repeat: true` and incur a `-0.02` reward penalty.

## Scoring Breakdown

`EpiGrader.grade()` weights:
- Pathogen identification: **25%** (synonym-aware, partial credit for correct genus)
- Source identification: **25%** (synonym-aware)
- Transmission route: **20%** (alias-aware: `"foodborne"`, `"food"`, `"food-borne"` all accepted)
- Case definition quality: **15%** (needs `clinical`, `time`, and `place`/`exposure` fields)
- Efficiency: **15%** (full credit if `steps ≤ optimal_steps`, zero at `max_steps`)

## Scenario Determinism

`ScenarioGenerator.generate(task_id, seed)` is fully reproducible. `data/` JSON files define the universe of pathogens, food vehicles, and settings. The `hard` task generates two simultaneous overlapping outbreaks. Food-pathogen compatibility is enforced via `FOOD_VEHICLES[key]["associated_pathogens"]`.

## Key Conventions

- **Case IDs** follow `c000`, `c001`, ... (`f"c{index:03d}"`)
- **Pathogen/source keys** use `snake_case` (e.g., `s_aureus`, `potato_salad`). The grader normalizes with `.lower().replace(" ", "_").replace("-", "_")` before comparing — synonyms are defined in `data/pathogens.json` and `data/food_vehicles.json`.
- **Port**: always `7860` (HF Spaces default). The old echo scaffold used 8000 — ignore any reference to it.
- **DATA_DIR** in `engine/scenario_generator.py` resolves as `Path(__file__).parent.parent / "data"`, so `data/` must be a sibling of `engine/` (both inside `epi_detective/`).
- **`inference.py` env vars**: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`, `ENV_URL`

## Deployment

```bash
# Docker (from epi_detective/ directory)
docker build -t epi-detective .
docker run -p 7860:7860 epi-detective

# HF Spaces via openenv CLI
pip install openenv-core
openenv push --repo-id your-username/epi-detective

# Manual HF Spaces: New Space → Docker → upload epi_detective/ contents → set port 7860
```

