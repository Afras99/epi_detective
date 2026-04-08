# Hackathon Rules, Judging Criteria & Submission Guide

> Consolidated from the Meta PyTorch OpenEnv Hackathon x SST (India, 2026) official sources.

---

## Timeline

| Phase | Dates | Format |
|-------|-------|--------|
| **Round 1** | March 28 – April 5, 2026 | Online (solo or team up to 3) |
| **Results declared** | After April 5 | Access Round 2 prep from dashboard |
| **Round 2 Bootcamp** | Weekend after results | Online — advanced RL, meta-learning, optimization |
| **Finale (Round 3)** | April 25–26, 2026 | 48-hour in-person hackathon at Scaler School of Technology, Bangalore |

---

## What you're building

> "Build a complete, real-world OpenEnv environment that an AI agent can learn from through the standard step() / reset() / state() API."

### Core requirements

1. **OpenEnv-compatible environment** — must implement `step()`, `reset()`, `state()` using the OpenEnv framework
2. **Minimum 3 tasks** with graders (easy → medium → hard, scores 0.0–1.0)
3. **Meaningful reward function** with partial progress signals (not sparse)
4. **Deploy to Hugging Face Spaces** with working Dockerfile
5. **Inference script** named `inference.py` in root directory
6. **Uses OpenAI Client** for all LLM calls
7. **Must run on:** vcpu=2, memory=8GB
8. **Inference must complete under 20 minutes**

### Required environment variables

Before submitting, these must be defined in your environment configuration:

```
API_BASE_URL    — The API endpoint for the LLM
MODEL_NAME      — The model identifier to use for inference
HF_TOKEN        — Your Hugging Face / API key
```

### Submission format

- Push to GitHub or HF
- Deploy to HF Spaces
- Paste your HF Spaces URL on the hackathon platform before deadline
- Only team leaders can make the final submission

---

## Judging criteria (Round 1)

### 1. Real-world utility — 30% weight

> "Does the environment model a genuine task? Would someone actually use this to train or evaluate agents?"

| Score | Description |
|-------|-------------|
| **26–30** | Excellent — fills a real gap, immediate value for the RL/agent community |
| **16–25** | Good domain modeling, useful for agent evaluation |
| **6–15** | Valid domain but shallow modeling |
| **0–5** | Toy problem or unrealistic abstraction |

**What judges look for:**
- Is this a task that real professionals do?
- Would the RL/agent community actually use this environment?
- Does it model a genuine sequential decision-making problem?
- Is the domain underserved by existing benchmarks?

**EpiDetective alignment:** CDC's 13-step outbreak investigation is performed thousands of times yearly. Post-COVID, universal understanding of stakes. Zero existing RL benchmarks cover epidemiological investigation.

---

### 2. Task & grader quality — 25% weight

> "Well-defined tasks, accurate graders, meaningful difficulty progression, hard task genuinely challenges frontier models."

**What judges look for:**
- Are tasks clearly defined with unambiguous success criteria?
- Do graders produce accurate, deterministic scores?
- Is there genuine difficulty progression (easy → medium → hard)?
- Does the hard task actually challenge frontier models (not just add more data)?
- Are there edge cases handled properly?

**EpiDetective alignment:**
- Task 1 (Easy): Single pathogen, single source — solvable by systematic evidence gathering
- Task 2 (Medium): Signal vs noise problem — must distinguish Legionella from concurrent flu
- Task 3 (Hard): Multi-hypothesis reasoning — must discover and separate two overlapping outbreaks
- All grading is fully deterministic against planted ground truth — no LLM-in-the-loop evaluation

---

### 3. Environment design — 20% weight

> "Clean state management, sensible action/observation spaces, good reward shaping, proper episode boundaries."

**What judges look for:**
- Clean, well-typed state representation
- Action space that makes sense for the domain
- Observation space that provides enough info without leaking answers
- Dense reward function (not just 0/1 at the end)
- Proper episode boundaries (clear start/end conditions)
- Information gating (agent must choose what to investigate)

**EpiDetective alignment:**
- Typed Pydantic models for Action (10 commands) and Observation
- Evidence gating creates genuine sequential decision-making
- Dense reward: +0.03 to +0.08 per evidence request, -0.02 for redundancy
- Hypothesis testing gives partial feedback mid-investigation
- Clear episode boundaries: reset() starts new case, submit_final_answer() ends it

---

### 4. Code quality & spec compliance — 15% weight

> "OpenEnv spec, clean structure, typed models, Dockerfile works, HF Space deploys."

**What judges look for:**
- Follows OpenEnv spec correctly (step/reset/state API)
- Clean project structure
- Typed Pydantic models
- Dockerfile builds and runs without errors
- HF Space deploys and responds
- `openenv validate` passes
- `inference.py` works with the specified env vars

**Checklist:**
- [ ] `openenv.yaml` present and valid
- [ ] `pyproject.toml` with all dependencies
- [ ] `models.py` with typed Action/Observation
- [ ] `server/epi_environment.py` extends Environment base class
- [ ] `client.py` extends HTTPEnvClient
- [ ] `inference.py` in root, uses OpenAI Client
- [ ] `Dockerfile` builds, runs on 2 vCPU / 8GB RAM
- [ ] HF Space URL accessible
- [ ] `openenv validate` passes all checks

---

### 5. Creativity & novelty — 10% weight

> "Novel domain, interesting mechanics, clever reward design."

**What judges look for:**
- Is this domain unique among submissions?
- Are there interesting mechanics beyond basic Q&A?
- Is the reward design clever (not just accuracy matching)?
- Would this environment be interesting to work with?

**EpiDetective alignment:**
- Epidemiology is completely uncharted territory for RL environments
- Investigation metaphor with information gating is inherently engaging
- Attack rate / odds ratio calculations add statistical reasoning dimension
- Reward design includes information value estimation, not just final accuracy

---

## Phase 2: Automated LLM evaluation

> After automated validation, they run a "standard Open LLM agent (e.g. Nemotron 3 Super)" against ALL environments.

### What this means for your environment

1. **Must be solvable** — the LLM agent must make meaningful progress
2. **Must differentiate** — good agents should score higher than bad ones
3. **Action format must be LLM-friendly** — text commands that an LLM can generate
4. **Observations must be text-parseable** — narratives + structured data that LLMs can reason about

### Design implications

- Action space uses natural language commands (not numeric action indices)
- Observations include both structured JSON and natural language narratives
- Available actions are explicitly listed in every observation
- Error handling for malformed agent actions (return helpful error, don't crash)
- Step budget prevents infinite loops

### Expected Nemotron scores for EpiDetective

| Task | Expected score range | Why |
|------|---------------------|-----|
| Easy | 0.60–0.85 | Systematic evidence gathering → pattern matching |
| Medium | 0.35–0.60 | Must distinguish signal from noise |
| Hard | 0.15–0.40 | Multi-hypothesis reasoning challenges even frontier models |

---

## Phase 3: Human review

> Top submissions reviewed by Meta and Hugging Face engineers for real-world utility, creativity, and exploit checks.

### Exploit checks they'll look for

- **Gaming the reward**: Can the agent get high scores without actually solving the problem?
  - Mitigation: Final grade is based on correctness components, not accumulated step rewards
- **Leaking ground truth**: Does the observation space accidentally reveal the answer?
  - Mitigation: Evidence is gated — lab results only appear when requested, not in initial alert
- **Degenerate strategies**: Can the agent just submit random answers and get lucky?
  - Mitigation: 25 pathogens × 15+ food vehicles × 5 routes = very low random success probability
- **Memorization**: Can the agent memorize scenario templates?
  - Mitigation: Parameterized randomization with seeds ensures unique scenarios

### What impresses Meta/HF engineers

- Clean, well-documented code
- Genuine domain expertise reflected in the environment
- Dense, well-motivated reward function
- Interesting agent behavior (not just keyword matching)
- Scalability — could this become a standard benchmark?

---

## Prizes & opportunities

- **$30,000 total prize pool**
- **Direct interview opportunity** with AI teams at Meta and Hugging Face
- Official Meta certificates
- Work becomes part of the OpenEnv open-source ecosystem
- Published on PyTorch blog (for top submissions)

---

## Already saturated domains (AVOID)

### Heavily saturated (10+ submissions each)
- SQL generation/debugging/analytics
- Email triage/inbox management
- Contract/legal review
- Code review environments
- CSV/data cleaning

### Moderately saturated (3-5 submissions)
- Financial AML/forensics
- Medical OCR/prescription parsing
- SOC alert triage / cybersecurity alert classification
- Adaptive firewall management
- HR compliance review
- Healthcare appointment scheduling
- Attendance validation
- Study planner
- Support ops / customer service
- DevOps cluster triage / SRE incident management

### Already in official OpenEnv repo
- Coding environment (Python execution)
- Chess, Atari, Snake, Connect4
- Financial RL (FinRL)
- Autonomous driving (CARLA)
- Browser automation (BrowserGym)
- Traffic simulation (SUMO RL)
- Wildfire simulation
- Poker/Blackjack/OpenSpiel games
- Git operations
- REPL environments
- Text arena / Wordle

---

## Technical setup requirements

### Before Round 1 opens

```bash
# Install Python 3.10, 3.11, or 3.12
python --version

# Install OpenEnv CLI
pip install openenv-core

# Verify
openenv --version

# Docker (for local testing)
docker --version
```

### Scaffold your project

```bash
openenv init epi_detective
cd epi_detective
```

### Local development loop

```bash
# Edit code → build → validate → test
openenv build
openenv validate
uvicorn server.app:app --host 0.0.0.0 --port 7860

# In another terminal:
python inference.py
```

### Deploy

```bash
openenv push --repo-id your-username/epi-detective
```

---

## Key links

| Resource | URL |
|----------|-----|
| Hackathon dashboard | https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/dashboard |
| OpenEnv GitHub repo | https://github.com/meta-pytorch/OpenEnv |
| OpenEnv documentation | https://meta-pytorch.org/OpenEnv/ |
| Building an environment guide | https://meta-pytorch.org/OpenEnv/environment-builder/ |
| OpenEnv Hub (HF Spaces) | https://huggingface.co/openenv |
| Hackathon Discord | Join from dashboard |
| OpenEnv RFC 001 (Abstractions) | https://github.com/meta-pytorch/OpenEnv/blob/main/rfcs/001-abstractions.md |
| OpenEnv RFC 002 (Env Spec) | https://github.com/meta-pytorch/OpenEnv/blob/main/rfcs/002-env-spec.md |
| PyTorch announcement | https://pytorch.org/event/openenv-ai-hackathon/ |
