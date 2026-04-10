---
title: Epi Detective
emoji: 🦠
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# EpiDetective — Disease Outbreak Investigation Environment

An OpenEnv-compatible reinforcement learning environment where AI agents investigate disease outbreaks by strategically gathering evidence, forming hypotheses, and identifying pathogens, contamination sources, and transmission routes.

Built for the **Meta PyTorch OpenEnv Hackathon** (India, 2026).

**Live demo:** [huggingface.co/spaces/Afras/epi-detective](https://huggingface.co/spaces/Afras/epi-detective)

---

## Why this environment matters

Outbreak investigation is a genuine professional workflow performed thousands of times yearly by epidemiologists at CDC, WHO, and state health departments. The CDC teaches it as a structured 13-step process. Post-COVID, every judge and engineer understands the stakes.

**No existing RL benchmark covers epidemiological investigation.** This environment fills a critical gap in the agent evaluation landscape.

---

## How it works

The agent receives an outbreak alert and must strategically request evidence — line lists, lab results, exposure histories, epi curves, environmental samples — to identify:

1. **The pathogen** (e.g., Salmonella Typhimurium)
2. **The contamination source** (e.g., potato salad)
3. **The transmission route** (e.g., foodborne)

Each scenario has planted ground truth, enabling fully deterministic grading with no LLM-in-the-loop evaluation.

---

## Three tasks with escalating difficulty

| Task | Max Steps | Scenario | Key challenge |
|------|-----------|----------|---------------|
| **easy** | 15 | Point-source foodborne outbreak at a shared meal | Single pathogen, single source, multiple red herrings |
| **medium** | 25 | Community-wide foodborne outbreak across multiple locations | Concurrent seasonal illness creates signal/noise problem |
| **hard** | 35 | Two overlapping outbreaks in same metro area | Must separate two clusters, identify both pathogens + sources |

---

## Quick start

```bash
# Run locally
cd epi_detective
pip install -r requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Reset and start an investigation
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy", "seed": 42}'

# Take a step
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"command": "request_line_list", "parameters": {}}'
```

---

## Run the inference agent

```bash
export HF_TOKEN="hf_your_token_here"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export ENV_URL="http://localhost:7860"   # or https://afras-epi-detective.hf.space

python epi_detective/inference.py
```

---

## Project structure

```
epi_detective/
├── Dockerfile
├── requirements.txt
├── openenv.yaml              # 3 tasks, port 7860
├── inference.py              # ReAct-style LLM agent (OpenAI client)
├── models.py                 # EpiAction, EpiObservation (Pydantic)
├── client.py                 # HTTP client helper
├── data/
│   ├── pathogens.json        # 21 pathogen profiles (CDC/FDA-sourced, see below)
│   ├── food_vehicles.json    # 15 food vehicles with pathogen associations (FDOSS-sourced)
│   └── settings.json         # 6 outbreak venues (NORS setting classifications)
├── engine/
│   ├── scenario_generator.py # Seeded scenario generation for all 3 tasks
│   └── evidence_engine.py    # Information gating — 9 investigation handlers
├── grader/
│   └── grader.py             # Deterministic 5-component grader + step rewards
└── server/
    └── app.py                # FastAPI: /reset /step /state /schema /health
```

---

## Epidemiological data sources

All scenario data is grounded in published CDC and FDA surveillance research — no numbers were invented.

**`pathogens.json` — 21 pathogen profiles:**
- **CDC "Confirming an Etiology" tables** — incubation periods and lab confirmation criteria (e.g., Salmonella median incubation 24h, lab confirmation via culture or CIDT)
- **FDA Bad Bug Book, 2nd Edition** — symptom profiles, food vehicle associations, and contamination mechanisms for each organism
- **Chai et al. (2019)** — statistically validated incubation period distributions derived from 16 years of FDA Outbreak Data Reporting System (FDOSS) data. Used for the lognormal incubation model in scenario generation.

**`food_vehicles.json` — 15 food vehicles:**
- **NORS/BEAM Dashboard** — CDC's National Outbreak Reporting System, showing empirical pathogen-food pairings from reported U.S. outbreaks
- **FDOSS surveillance summaries (2009–2022)** — attack rates and food associations (e.g., Salmonella ↔ poultry/eggs, E. coli O157:H7 ↔ ground beef/leafy greens)

**`settings.json` — 6 outbreak venues:**
- **NORS setting classifications** — the venue categories CDC uses for classifying reported outbreaks (restaurant, catering/banquet, school, private residence, institution, etc.)

All data is loaded from static JSON files at server startup — no API calls, no internet dependency at runtime.

---

## Judging criteria alignment

| Criterion | Weight | Why EpiDetective scores well |
|-----------|--------|------------------------------|
| Real-world utility | 30% | Directly models CDC's 13-step outbreak investigation protocol |
| Task & grader quality | 25% | Deterministic grading against planted ground truth, 5-component scorer |
| Environment design | 20% | Information-gating creates genuine sequential decision-making |
| Code quality & spec | 15% | OpenEnv-compliant, typed Pydantic models, seeded reproducibility |
| Creativity & novelty | 10% | No existing RL benchmarks in epidemiology |

---

## License

MIT
