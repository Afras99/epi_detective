# Build Schedule — Day by Day

## Day 1: Data Layer (6-8 hours)

### Goal: All JSON data files created and validated

**Morning (3-4h): Curate pathogen knowledge base**

- [ ] Open CDC Etiology Tables: https://www.cdc.gov/foodborne-outbreaks/php/confirming-cause/index.html
- [ ] Open FDA Organism Chart: https://www.fda.gov/media/77727/download
- [ ] Open Chai et al. (2019): https://pmc.ncbi.nlm.nih.gov/articles/PMC6805792/
- [ ] Create `data/pathogens.json` with all 25 organisms from PATHOGEN_KNOWLEDGE_BASE.md
- [ ] Validate: every pathogen has incubation, symptoms with frequencies, common foods, synonyms
- [ ] Cross-check incubation periods against Chai et al. Table 1

**Afternoon (3-4h): Food vehicles, settings, synonyms**

- [ ] Create `data/food_vehicles.json` — 15+ food vehicles with pathogen associations
- [ ] Create `data/settings.json` — 6+ outbreak settings with parameters
- [ ] Create `data/synonym_sets.json` — comprehensive fuzzy matching sets
- [ ] Create `data/symptoms.json` — symptom-to-pathogen reverse lookup for grading
- [ ] Test: load all JSON files in Python, validate schema

**Data source checklist:**
- [ ] Downloaded NORS BEAM Dashboard export (CSV) for reference attack rates
  - URL: https://wwwn.cdc.gov/norsdashboard/ → NORS View → Tabular → Download
- [ ] Bookmarked FDA Bad Bug Book PDF for detailed pathogen descriptions
  - URL: https://www.fda.gov/files/food/published/Bad-Bug-Book-2nd-Edition-(PDF).pdf
- [ ] Verified Faker library generates realistic US names/demographics
  - `pip install faker` → test `Faker('en_US').name()`

---

## Day 2: Scenario Generator (6-8 hours)

### Goal: `engine/scenario_generator.py` produces complete, valid scenarios

**Morning (3-4h): Core generation pipeline**

- [ ] Create `engine/scenario_generator.py` — main ScenarioGenerator class
- [ ] Implement pathogen + food vehicle sampling
- [ ] Implement population generation (Faker demographics)
- [ ] Implement exposure matrix builder (guilty food vs red herring vs neutral)
- [ ] Test: generate 10 easy scenarios, verify attack rate distributions

**Afternoon (3-4h): Evidence layers + case generation**

- [ ] Create `engine/case_generator.py` — individual case generation
- [ ] Create `engine/epi_curve.py` — onset time distribution (log-normal)
- [ ] Implement symptom assignment using pathogen frequency data
- [ ] Implement lab result generation
- [ ] Implement alert narrative generation from templates
- [ ] Create `engine/stats.py` — attack rate and odds ratio calculators
- [ ] Test: full scenario generation for all 3 task types
- [ ] Verify: guilty food ALWAYS has highest relative risk in easy scenarios

**Validation criteria:**
```python
# These must pass for every generated scenario:
assert scenario.ground_truth["pathogen"] in PATHOGENS
assert len(scenario.evidence["line_list"]["data"]) > 0
assert scenario.ground_truth["source"] in FOOD_VEHICLES
assert all(case["onset_datetime"] for case in ill_cases)
attack_rate = calculate_attack_rate(scenario, scenario.ground_truth["source"])
assert attack_rate["relative_risk"] > 3.0  # Guilty food must be clearly associated
```

---

## Day 3: OpenEnv Server (6-8 hours)

### Goal: Working FastAPI server with step/reset/state

**Morning (3-4h): Environment + evidence engine**

- [ ] Create `models.py` — EpiAction, EpiObservation
- [ ] Create `engine/evidence_engine.py` — information gating logic
- [ ] Create `server/epi_environment.py` — EpiDetectiveEnvironment class
- [ ] Implement `reset()` — generate scenario, return initial alert
- [ ] Implement `step()` — process actions, return gated evidence
- [ ] Implement `state()` — return current investigation state

**Afternoon (3-4h): Server + client**

- [ ] Create `server/app.py` — FastAPI application wrapping the environment
- [ ] Create `client.py` — typed EnvClient
- [ ] Create `openenv.yaml`
- [ ] Test locally: `uvicorn server.app:app --port 7860`
- [ ] Manual test: send reset → step (request_line_list) → step (calculate_attack_rate) → step (submit_final_answer)
- [ ] Verify WebSocket connection works

---

## Day 4: Grader + Reward (4-6 hours)

### Goal: Deterministic grading that produces correct scores

**Morning (2-3h): Core grading logic**

- [ ] Create `grader/grader.py` — EpiGrader class
- [ ] Implement pathogen matching (exact + synonym + partial genus)
- [ ] Implement source matching (exact + synonym + category partial)
- [ ] Implement route matching (categorical)
- [ ] Implement case definition quality scoring
- [ ] Implement efficiency scoring (linear decay)

**Afternoon (2-3h): Dense reward + testing**

- [ ] Create `grader/reward.py` — per-step reward function
- [ ] Implement evidence value rewards (+0.03 to +0.08)
- [ ] Implement redundancy penalty (-0.02)
- [ ] Implement hypothesis partial feedback
- [ ] Write `tests/test_grader.py` — test all scoring edge cases:
  - [ ] Perfect submission → score ≈ 1.0
  - [ ] Correct pathogen, wrong source → score ≈ 0.45-0.55
  - [ ] Everything wrong → score ≈ 0.0
  - [ ] Synonym matching works ("salmonella" = "salmonella_enterica")
  - [ ] Efficiency scoring: 8 steps → 1.0, 12 steps → ~0.43, 15 steps → 0.0

---

## Day 5: Inference Script + Agent Loop (4-6 hours)

### Goal: `inference.py` successfully completes all 3 tasks

**Morning (2-3h): Agent implementation**

- [ ] Create `inference.py` — LLM agent using OpenAI Client
- [ ] Implement ReAct parsing (THOUGHT + ACTION format)
- [ ] Implement action parsing with fallback logic
- [ ] Implement conversation management (full history per episode)

**Afternoon (2-3h): Agent testing + optimization**

- [ ] Test with local LLM or API endpoint
- [ ] Run agent on Task 1 (easy) — target score: >0.60
- [ ] Run agent on Task 2 (medium) — target score: >0.35
- [ ] Run agent on Task 3 (hard) — target score: >0.15
- [ ] Tune system prompt based on agent behavior
- [ ] Add error handling for malformed LLM responses
- [ ] Verify inference completes within 20 minutes for all 3 tasks

---

## Day 6: Docker + HF Spaces Deployment (4-6 hours)

### Goal: Environment running on Hugging Face Spaces

**Morning (2-3h): Docker**

- [ ] Create `server/Dockerfile`
- [ ] Create `server/requirements.txt`
- [ ] Build locally: `docker build -t epi-detective .`
- [ ] Run locally: `docker run -p 7860:7860 epi-detective`
- [ ] Test all endpoints from outside container
- [ ] Verify memory usage < 1GB

**Afternoon (2-3h): HF Spaces deployment**

- [ ] Create Hugging Face Space
- [ ] `openenv push --repo-id your-username/epi-detective`
- [ ] Verify Space is running
- [ ] Run `openenv validate` against deployed Space
- [ ] Test inference script against deployed Space URL
- [ ] Verify the Gradio web UI works for manual interaction

**Deployment checklist:**
- [ ] Environment variables configured: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`
- [ ] Dockerfile builds without errors
- [ ] Space responds to WebSocket connections
- [ ] reset/step/state all return valid responses
- [ ] Inference completes within 20 minutes

---

## Day 7: Polish + Submission (4-6 hours)

### Goal: Submission-ready with excellent documentation

**Morning (2-3h): Edge cases + difficulty tuning**

- [ ] Run 50+ random scenarios per task level, check for:
  - [ ] Scenarios where guilty food has RR < 2.0 (too hard for easy) → fix
  - [ ] Scenarios where all attack rates are similar (no clear signal) → fix
  - [ ] Lab results that don't match the planted pathogen → fix
  - [ ] Empty line lists or missing data → fix
- [ ] Tune Task 1 red herring difficulty (ensure RR gap between guilty and highest red herring > 3x)
- [ ] Verify Task 3 two-outbreak separation is possible from lab results alone

**Afternoon (2-3h): Documentation + final submission**

- [ ] Write comprehensive README.md
- [ ] Add docstrings to all public functions
- [ ] Clean up code (remove debug prints, commented code)
- [ ] Final `openenv validate` pass
- [ ] Final inference run → record scores
- [ ] Push to GitHub
- [ ] Submit HF Spaces URL on hackathon platform
- [ ] Celebrate

---

## Quick reference: Environment variable setup

```bash
# For inference script (set by hackathon platform)
export API_BASE_URL="https://api-inference.huggingface.co/v1"
export MODEL_NAME="nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"
export HF_TOKEN="hf_your_token_here"

# For local development
export ENV_URL="http://localhost:7860"
```

## Quick reference: Key commands

```bash
# Scaffold
openenv init epi_detective

# Build & test
openenv build
openenv validate

# Run locally
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Deploy
openenv push --repo-id your-username/epi-detective

# Run tests
pytest tests/ -v

# Run inference
python inference.py
```
