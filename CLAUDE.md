# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**EpiDetective** is an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) RL environment where an AI agent plays field epidemiologist, investigating simulated disease outbreaks by gathering evidence and identifying the pathogen, food source, and transmission route.

The project has two halves:
- **Server** (`epi_detective/`): A self-contained FastAPI app serving the environment over HTTP on port 7860.
- **Agent** (`inference.py`): A ReAct-style LLM agent that interacts with the server and produces hackathon-required log output.

## Commands

Run from the **`epi_detective/`** directory (where `pyproject.toml` lives):

```bash
# Install dependencies
pip install fastapi uvicorn pydantic openai requests

# Run the server (development)
uvicorn server.app:app --reload --host 0.0.0.0 --port 7860

# Run tests
python -m pytest tests/test_core.py -v

# Run a single test class
python -m pytest tests/test_core.py::TestGrader -v
```

Run the agent from the **repo root**:

```bash
# Against local server
ENV_URL=http://localhost:7860 HF_TOKEN=<token> python inference.py

# Against HF Space
ENV_URL=https://afras-epi-detective.hf.space HF_TOKEN=<token> python inference.py
```

## Architecture

### Key files

| File | Role |
|---|---|
| `epi_detective/models.py` | Canonical Pydantic types: `EpiAction` (agent input) and `EpiObservation` (base response). Imported by `server/app.py`. |
| `epi_detective/server/app.py` | FastAPI app. `ActionRequest` extends `EpiAction`; `StepResponse` extends `EpiObservation`. Exposes `/reset`, `/step`, `/state`, `/health`, `/schema`. |
| `epi_detective/engine/scenario_generator.py` | Deterministic outbreak generation from `(task_id, seed)`. Produces `Scenario` with patients, exposure matrix, lab results, ground truth. |
| `epi_detective/engine/evidence_engine.py` | Information gating — 9 handlers map investigation commands to CDC 13-step protocol. Tracks unlocked evidence and action history. |
| `epi_detective/grader/grader.py` | `EpiGrader.grade()` — 5-component scorer (pathogen 25%, source 25%, route 20%, case_definition 15%, efficiency 15%). Scores clamped to (0.001, 0.999). |
| `epi_detective/data/pathogens.json` | 21 pathogens with incubation periods, symptoms, lab methods, synonyms. |
| `epi_detective/data/food_vehicles.json` | 15 food vehicles with associated pathogens and synonyms. |
| `epi_detective/data/settings.json` | Event venue types (county fair, wedding, etc.) with typical menus. |
| `epi_detective/tests/test_core.py` | 26 tests covering grader, scenario generator, evidence engine. |
| `epi_detective/Dockerfile` | python:3.11-slim, port 7860, HEALTHCHECK via urllib.request. |
| `epi_detective/openenv.yaml` | OpenEnv manifest. |
| `inference.py` | ReAct-style LLM agent (repo root — required by hackathon spec). |

### Three task difficulties

| Task | Pathogen pool | Attendees | Max steps | Notes |
|---|---|---|---|---|
| `easy` | s_aureus, c_perfringens, salmonella, norovirus, e_coli_o157 | 30–80 | 15 | Single pathogen, clear food signal |
| `medium` | campylobacter, listeria, shigella, hepatitis_a, cyclospora | 80–150 | 25 | More noise, subtler signal |
| `hard` | Two simultaneous outbreaks (e_coli_o157/salmonella + norovirus/s_aureus) | 150–250 | 35 | Dual pathogens, grader credits either |

### Investigation flow (CDC 13-step model)

1. `view_initial_alert` → outbreak notification (+0.02)
2. `request_line_list` → patient demographics, onset times, symptoms (+0.05)
3. `generate_epi_curve` → cases by hour, point-source vs propagated (+0.03)
4. `request_lab_results` → pathogen from clinical specimens (+0.08)
5. `get_exposure_history` → what patients ate (required before attack rate) (+0.05)
6. `calculate_attack_rate` → 2×2 table + relative risk per food (+0.05, +0.05 bonus if correct food)
7. `calculate_odds_ratio` → OR for food-illness association (+0.04)
8. `request_environmental_samples` → kitchen swab results (+0.04)
9. `submit_hypothesis` → per-component feedback, max 3 attempts (no reward)
10. `submit_final_answer` → ends episode, triggers grader, returns final score

Repeat actions: **-0.02**. `calculate_attack_rate` blocked until `get_exposure_history` called.

### Reward system

- **Per-step rewards**: +0.02 to +0.08 for new evidence, -0.02 for repeats (training signal)
- **Final score**: grader output on `submit_final_answer` — the only value reported in `[END]`
- **Scores**: always clamped to (0.001, 0.999) exclusive

### Session management

`/reset` accepts optional `session_id`. If omitted, uses `"default"`. Multiple sessions can run concurrently with independent state. Backward compatible — existing inference scripts without session_id use the default session.
