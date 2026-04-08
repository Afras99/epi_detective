# Meta × PyTorch × Hugging Face — OpenEnv Hackathon: Round 1 Guide

> **Hosted by:** Scaler School of Technology  
> **Submission Deadline:** 8th April 2026, 11:59 PM IST  
> **Support:** help_openenvhackathon@scaler.com  
> **Community:** [Join Discord](https://discord.gg/Dedhy5pkWD)

---

## Table of Contents

1. [Event Timeline](#event-timeline)
2. [What to Expect](#what-to-expect)
3. [Prerequisites](#prerequisites)
4. [Problem Statement](#problem-statement)
5. [Required Files & Project Structure](#required-files--project-structure)
6. [Functional Requirements](#functional-requirements)
7. [Non-Functional Requirements](#non-functional-requirements)
8. [Environment Variables](#environment-variables)
9. [Pre-Submission Checklist](#pre-submission-checklist)
10. [Evaluation Criteria](#evaluation-criteria)
11. [How to Submit](#how-to-submit)
12. [Infrastructure Restrictions](#infrastructure-restrictions)
13. [FAQs](#faqs)
14. [Getting Help](#getting-help)

---

## Event Timeline

| Phase | Dates |
|---|---|
| Registration | 14th March – 3rd April |
| Declaration (Solo/Team) | Before Round 1 |
| Prepare (Bootcamp & Study) | Now – 25th March |
| **Round 1 (Build & Submit)** | **25th March – 8th April** |
| Results Announced | 10th April |
| Finale (In-Person) | 25th–26th April |

---

## What to Expect

Round 1 is an **online build challenge**. You will:

1. **Choose a problem statement** — Select one from 4–5 real-world challenge options revealed on the platform on 1st April.
2. **Scaffold your project** — Use the OpenEnv CLI to generate the project structure automatically.
3. **Build** — Implement your RL environment in the generated files.
4. **Test locally** — Run the local server and validate your environment before deploying.
5. **Deploy** — Push your environment as a containerised Hugging Face Space.
6. **Submit** — Paste your HF Spaces URL on the dashboard before the deadline.

Round 1 uses an **LLM-based evaluator with structured rubrics**. Top 3,000 teams advance to the Grand Finale — a **48-hour in-person hackathon** judged by Meta's global team.

---

## Prerequisites

### Knowledge
- Python (intermediate level)
- Basic understanding of Reinforcement Learning concepts (reward functions, observations, actions)
- Familiarity with REST APIs / FastAPI is helpful
- Basic Docker knowledge (build & run containers)

### Tools & Accounts
- A **Hugging Face account** (free) — required for deployment to Hugging Face Spaces
- **Git** installed locally
- **Docker** installed locally (for local testing and containerisation)
- **Python 3.10+** with `uv` or `pip` package manager
- The **OpenEnv** framework installed: `pip install openenv`

### Recommended Preparation
Complete the 4-module Preparatory Course (~3.5 hours total) on the dashboard:

| Module | Topic | Time | Priority |
|---|---|---|---|
| 1 | Why OpenEnv? | 45 min | Essential |
| 2 | Using Existing Environments | 50 min | Essential |
| 3 | Deploying Environments | 45 min | Essential |
| 4 | Building Your Own Environment | 60 min | **Most Important** |

📖 [View full course repository](https://github.com/raun/openenv-course/tree/main)

---

## Problem Statement

### The Task
Build a **complete, real-world OpenEnv environment** that an AI agent can learn from through the standard `step()` / `reset()` / `state()` API.

The environment must simulate a **real-world task** — not a game or toy problem. Accepted domains include:

- Email triage
- Code review
- Data cleaning
- Scheduling
- Customer support
- Content moderation
- (And similar real-world workflows)

---

## Required Files & Project Structure

Your submitted GitHub repository **must** contain the following:

```
my_env/
├── openenv.yaml          # Environment metadata (required)
├── Dockerfile            # Container build file (required)
├── requirements.txt      # Python dependencies (required)
├── inference.py          # Baseline inference script (required — must be in root)
├── README.md             # Documentation (required)
└── <environment code>    # Your OpenEnv implementation files
```

### File Descriptions

| File | Description |
|---|---|
| `openenv.yaml` | Metadata file describing the environment. Must pass `openenv validate`. |
| `Dockerfile` | Containerises the environment. Must build and run cleanly via `docker build` + `docker run`. |
| `requirements.txt` | All Python dependencies needed to run the environment. |
| `inference.py` | Baseline script that runs a model against the environment. Must be in the root directory. |
| `README.md` | Documents the environment: description, action/observation spaces, task list, setup instructions, baseline scores. |

---

## Functional Requirements

### 1. Real-World Task Simulation
- Environment must simulate a task humans actually perform (not games or toys).

### 2. Full OpenEnv Spec Compliance
Implement the complete OpenEnv interface:
- **Typed Pydantic models** for `Observation`, `Action`, and `Reward`.
- `step(action)` → returns `observation, reward, done, info`
- `reset()` → returns the initial observation
- `state()` → returns the current environment state
- `openenv.yaml` with environment metadata
- Must pass `openenv validate`

### 3. Minimum 3 Tasks with Agent Graders
- Each task must define a **concrete objective** an agent must accomplish.
- Tasks must scale in difficulty: **easy → medium → hard**.
- Each task must have a **programmatic grader** that scores performance from **0.0 to 1.0**.
- Graders must have clear, deterministic success/failure criteria.

### 4. Meaningful Reward Function
- Provides signal **across the full trajectory** (not just binary end-of-episode reward).
- Rewards **partial progress** toward task completion.
- Penalises clearly undesirable behaviour (e.g., infinite loops, destructive actions).

### 5. Baseline Inference Script (`inference.py`)
- Uses the **OpenAI API client** to run a model against the environment.
- Reads API credentials from **environment variables** (see below).
- Produces a **reproducible baseline score** on all 3 tasks.
- Must complete in **under 20 minutes**.

---

## Non-Functional Requirements

### Deployment
- Environment must run as a **containerised Hugging Face Space** tagged with `openenv`.

### Containerisation
- Must include a working `Dockerfile`.
- Environment must start cleanly with `docker build` + `docker run`.

### Documentation (README)
Your README must include:
- Environment description and motivation
- Action and observation space definitions
- Task descriptions with expected difficulty
- Setup and usage instructions
- Baseline scores

---

## Environment Variables

Before submitting, define the following environment variables in your configuration:

| Variable | Description |
|---|---|
| `API_BASE_URL` | The API endpoint for the LLM. |
| `MODEL_NAME` | The model identifier to use for inference. |
| `HF_TOKEN` | Your Hugging Face API key. |

> ⚠️ **Important:** All LLM calls in `inference.py` must use the **OpenAI client** with the above variables.

---

## Pre-Submission Checklist

All items below **must pass** or your submission will be **disqualified**:

- [ ] **HF Space deploys** — Automated ping to the Space URL must return `200` and respond to `reset()`.
- [ ] **OpenEnv spec compliance** — `openenv.yaml`, typed models, and `step()`/`reset()`/`state()` endpoints validated.
- [ ] **Dockerfile builds** — Automated docker build on the submitted repo must succeed.
- [ ] **Baseline reproduces** — The inference script runs without errors and produces scores.
- [ ] **3+ tasks with graders** — All tasks enumerated, graders run, scores in `0.0–1.0` range.

> 🔍 Run the **Pre-Validation Script** provided on the dashboard before submitting.

---

## Evaluation Criteria

Submissions are evaluated across these dimensions:

1. **Runtime correctness** — Does the environment run, and do the endpoints behave as expected?
2. **OpenEnv interface compliance** — Does the environment fully implement the spec?
3. **Task design quality** — Are the tasks meaningful, well-scoped, and appropriately tiered?
4. **Grading logic** — Are the graders deterministic, fair, and scoring in range?
5. **Overall code quality** — Is the code clean, readable, and well-documented?

---

## How to Submit

Follow these 6 steps:

### Step 1 — Choose a Problem Statement
Select **one** of the 4–5 problem statements revealed on the Scaler dashboard on **1st April**.

### Step 2 — Scaffold Your Project
```bash
openenv init my_env
```
This generates the base project structure for your environment.

### Step 3 — Build
Implement your environment logic inside the generated files. Define your typed models, tasks, graders, and reward functions.

### Step 4 — Test Locally
```bash
uv run server
```
Test your environment locally to ensure `step()`, `reset()`, and `state()` work correctly.

### Step 5 — Deploy to Hugging Face Spaces
```bash
openenv push --repo-id your-username/my-env
```
This containerises and deploys your environment as an HF Space.

### Step 6 — Submit
Paste your **Hugging Face Spaces URL** on the dashboard before the deadline.

> 📅 **Deadline: 8th April 2026, 11:59 PM IST**  
> ⚠️ **Only team leaders can make the final submission.**  
> ✅ You may update your submission multiple times before the deadline — only the latest will be evaluated.

---

## Infrastructure Restrictions

To ensure fair evaluation, all submissions must comply with these limits:

- **Maximum runtime** of `inference.py`: **20 minutes**
- **Machine spec**: vCPU = 2, RAM = 8 GB
- All LLM calls must use the **OpenAI client** (not direct model loading)

---

## FAQs

**Q: Do I need to complete the prep course?**  
Not mandatory, but strongly recommended — especially Module 4.

**Q: Can I compete solo?**  
Yes. Solo participants who qualify for Round 2 will be matched with others to form teams for the 48-hour finale.

**Q: Can I update my submission after submitting?**  
Yes, multiple times until the deadline. Only the latest submission counts.

**Q: What framework must I use?**  
All environments must be built using the **OpenEnv framework** by Meta and Hugging Face.

**Q: What happens after Round 1?**  
Results on 10th April. Top 3,000 teams advance to the Finale (25–26 April, in-person).

**Q: What exactly do I need to submit?**  
A public GitHub repository containing your environment code, `requirements.txt`, `inference.py`, and `README.md`, plus a deployed Hugging Face Spaces URL.

**Q: Who makes the final submission for a team?**  
Only the **team leader** can make the final submission.

---

## Getting Help

- 📧 Email: [help_openenvhackathon@scaler.com](mailto:help_openenvhackathon@scaler.com)
- 💬 Discord: [Join the community](https://discord.gg/Dedhy5pkWD) — announcements, mentor access, and team matching
- 📚 OpenEnv GitHub: [meta-pytorch/OpenEnv](https://github.com/meta-pytorch/OpenEnv)

---

*Last updated: April 2026*
