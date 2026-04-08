---
title: EpiDetective — Disease Outbreak Investigation Environment
emoji: 🔬
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
tags:
  - openenv
---

# EpiDetective

**A real-world OpenEnv environment where AI agents investigate disease outbreaks.**

EpiDetective simulates the work of a field epidemiologist responding to a foodborne illness cluster. The agent must gather evidence systematically — requesting patient records, lab results, exposure histories, and statistical analyses — then identify the causative pathogen, contaminated food source, and transmission route before running out of steps.

This is a genuine sequential decision-making problem: CDC field investigators follow exactly this workflow thousands of times per year. The environment models the full 9-step CDC outbreak investigation protocol as a reinforcement learning task.

---

## Environment Overview

| Property | Value |
|---|---|
| Action space | 10 discrete text commands with optional parameters |
| Observation space | Structured JSON + natural language narrative per step |
| Reward | Dense (per-step) + final score (0.0–1.0) |
| Episode length | 15 steps (easy) / 25 steps (medium) / 35 steps (hard) |
| Reproducibility | Fully seeded — same seed produces identical scenario |
| Concurrency | Single session (suitable for HF Spaces) |

---

## Tasks

### Task 1 — Easy: Point-Source Foodborne Outbreak
**`task_id: "easy"` | max_steps: 15 | optimal_steps: 8**

A single event (wedding, school lunch, church potluck) where a single contaminated food item caused illness in a fraction of attendees. The agent must identify which food was guilty by comparing attack rates across the menu.

- **Pathogen pool:** S. aureus, C. perfringens, Salmonella, Norovirus, E. coli O157
- **Challenge:** Distinguish the guilty food from 5–7 menu items using attack rate calculations
- **Expected score (strong agent):** 0.70–0.90

### Task 2 — Medium: Community Respiratory Outbreak
**`task_id: "medium"` | max_steps: 25 | optimal_steps: 14**

A Legionella cluster with concurrent seasonal influenza activity in the same population. The agent must separate signal from noise — some patients have Legionnaires' disease (environmental source), others have flu (unrelated).

- **Pathogen:** Legionella pneumophila
- **Challenge:** Distinguish a low-attack-rate environmental pathogen from background illness noise
- **Expected score (strong agent):** 0.45–0.65

### Task 3 — Hard: Multi-Source Overlapping Outbreaks
**`task_id: "hard"` | max_steps: 35 | optimal_steps: 20**

Two simultaneous outbreaks from different pathogens and food sources in a metro area. The agent must discover that cases do not share a single source, identify both outbreaks independently, and report both.

- **Pathogen pools:** E. coli O157 / Salmonella (outbreak A) + Norovirus / S. aureus (outbreak B)
- **Challenge:** Multi-hypothesis reasoning across overlapping patient populations
- **Expected score (strong agent):** 0.20–0.45

---

## Action Space

All actions are sent as `POST /step` with a `command` string and optional `parameters` dict.

| Command | Parameters | What it returns |
|---|---|---|
| `view_initial_alert` | none | The original outbreak notification narrative |
| `request_line_list` | none | All ill patients: age, sex, onset time, symptoms, hospitalisation |
| `generate_epi_curve` | `{"grouping": "hour"}` | Cases plotted by hour — reveals point-source vs propagated |
| `request_lab_results` | `{"case_ids": ["c001","c002"]}` | Pathogen identified per patient (65% positive rate) |
| `get_exposure_history` | `{"case_ids": ["c001"]}` | What each patient ate at the event |
| `calculate_attack_rate` | `{"food_item": "potato_salad"}` | Ate-ill vs ate-well 2×2 table + relative risk |
| `calculate_odds_ratio` | `{"exposure": "chicken"}` | Odds ratio for food-illness association |
| `request_environmental_samples` | `{"location": "kitchen"}` | Environmental swab results from venue |
| `submit_hypothesis` | `{"pathogen": "...", "source": "...", "route": "..."}` | Partial feedback (no reward, just guidance) |
| `submit_final_answer` | `{"pathogen": "...", "source": "...", "route": "...", "case_definition": {"clinical": "...", "time": "...", "place": "..."}}` | Triggers grader, ends episode |

---

## Observation Space

Every `POST /step` and `POST /reset` returns:

```json
{
  "observation": {
    "result_type": "line_list",
    "narrative": "Line list received: 23 cases identified. Age range: 18–72...",
    "data": { "cases": [...] },
    "available_actions": ["request_lab_results", "get_exposure_history", "..."],
    "step_reward": 0.05,
    "done": false
  },
  "reward": 0.05,
  "done": false,
  "state": {
    "step_count": 2,
    "steps_remaining": 13,
    "evidence_unlocked": ["initial_alert", "line_list"],
    "actions_taken": 2,
    "task_id": "easy"
  }
}
```

`result_type` values: `alert`, `line_list`, `epi_curve`, `lab_results`, `exposure_history`, `attack_rate`, `odds_ratio`, `environmental`, `hypothesis_feedback`, `final_score`, `error`

---

## Reward Function

### Per-step (dense) rewards

| Action | Reward |
|---|---|
| `request_line_list` | +0.05 |
| `request_lab_results` | +0.08 |
| `get_exposure_history` | +0.05 |
| `generate_epi_curve` | +0.03 |
| `calculate_attack_rate` (correct food) | +0.10 |
| `calculate_attack_rate` (other food) | +0.05 |
| `calculate_odds_ratio` | +0.04 |
| `request_environmental_samples` | +0.04 |
| `view_initial_alert` | +0.02 |
| Repeated action | −0.02 |

### Final score (on `submit_final_answer`)

| Component | Weight |
|---|---|
| Pathogen identified correctly | 25% |
| Food source identified correctly | 25% |
| Transmission route correct | 20% |
| Case definition quality (clinical + time + place) | 15% |
| Step efficiency (fewer steps = higher bonus) | 15% |

Pathogen and source matching uses fuzzy synonym matching — "salmonellosis", "S. typhimurium", and "salmonella_enterica" all count as correct for "salmonella".

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Returns `{"status": "healthy"}` |
| `/reset` | POST | Start new investigation. Body: `{"task_id": "easy", "seed": 42}` |
| `/step` | POST | Take one action. Body: `{"command": "...", "parameters": {...}}` |
| `/state` | GET | Current session state |
| `/schema` | GET | Action and observation schema |

---

## Baseline Scores

Scores achieved by a `meta-llama/Llama-3.1-8B-Instruct` ReAct agent via the included `inference.py`:

| Task | Score | Notes |
|---|---|---|
| Easy | ~0.65 | Systematic evidence gathering works well |
| Medium | ~0.40 | Signal/noise separation is harder |
| Hard | ~0.20 | Multi-outbreak discovery rarely achieved |

---

## Setup & Usage

### Run locally

```bash
cd epi_detective
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Test the server

```bash
# Health check
curl http://localhost:7860/health

# Start an investigation
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy", "seed": 42}'

# Request the patient line list
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"command": "request_line_list", "parameters": {}}'

# Submit a final answer
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"command": "submit_final_answer", "parameters": {"pathogen": "salmonella", "source": "chicken", "route": "foodborne", "case_definition": {"clinical": "diarrhea and fever", "time": "6-72h after meal", "place": "event venue"}}}'
```

### Run with Docker

```bash
docker build -t epi-detective .
docker run -p 7860:7860 epi-detective
```

### Run the inference agent

```bash
export API_BASE_URL="https://api-inference.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export HF_TOKEN="hf_your_token_here"
export ENV_URL="http://localhost:7860"

python inference.py
```

---

## Project Structure

```
epi_detective/
├── openenv.yaml          # Environment manifest (3 tasks, port 7860)
├── Dockerfile            # Python 3.11-slim, exposes 7860
├── requirements.txt      # fastapi, uvicorn, pydantic, openai, requests
├── inference.py          # ReAct-style LLM agent (OpenAI client)
├── models.py             # Typed Pydantic models: EpiAction, EpiObservation
├── client.py             # HTTP client helper
├── data/
│   ├── pathogens.json    # 21 pathogens with incubation, symptoms, synonyms
│   ├── food_vehicles.json # 15 food vehicles with pathogen associations
│   └── settings.json     # 6 outbreak venues with typical menus
├── engine/
│   ├── scenario_generator.py  # Seeded scenario generation for all 3 tasks
│   └── evidence_engine.py     # Information gating — 9 investigation handlers
├── grader/
│   └── grader.py         # Deterministic 5-component grader + step rewards
└── server/
    └── app.py            # FastAPI app: /reset /step /state /schema /health
```

---

## Real-World Grounding

EpiDetective is not a toy or game. It directly models the **CDC's canonical 13-step outbreak investigation framework** — the standard methodology used by epidemiologists at CDC, state health departments, and WHO. Every action in the environment corresponds to something a real public health investigator actually does during a foodborne illness outbreak.

Post-COVID, outbreak investigation is universally understood as high-stakes professional work. An agent trained in EpiDetective would develop skills directly transferable to automated outbreak detection and public health surveillance systems — an active area of applied AI research.

### Data Sources

All pathogen profiles, incubation periods, symptom frequencies, and food-pathogen associations are grounded in peer-reviewed epidemiological data:

| Source | What it provides |
|---|---|
| **CDC NORS / BEAM Dashboard** | 13,000+ real US outbreak records (1998–2022) — pathogen, food category, setting, contributing factors |
| **FDA Bad Bug Book, 2nd Edition** | Pathogen profiles: transmission routes, incubation ranges, clinical syndromes, confirmation criteria |
| **CDC "Foodborne Illness-Causing Organisms" table** | Standardised incubation periods and symptom profiles for 21 organisms |
| **Chai et al. (2019), FDOSS study** (PubMed Central) | Statistically grounded incubation distributions from 16 years of outbreak data — used to set median, min, max, and 70th-percentile ranges per pathogen |

The 21 pathogens cover bacterial intoxications (S. aureus, C. perfringens, botulism), bacterial infections (Salmonella, E. coli O157, Campylobacter, Legionella, Listeria), viral agents (Norovirus, Hepatitis A, Rotavirus), parasites (Cyclospora, Cryptosporidium, Trichinella), and natural toxins (Ciguatoxin, Scombroid).

Patient demographics, names, and exposure histories are synthetically generated — no real patient data is used.
