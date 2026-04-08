# The single best OpenEnv hackathon idea (and 4 strong alternatives)

**An epidemiology outbreak investigation environment is the optimal submission for the Meta PyTorch OpenEnv Hackathon.** It scores highest across every judging dimension: real-world utility (public health crisis detection), task quality (deterministic component-wise grading against planted ground truth), environment design (information-gating creates natural multi-step LLM reasoning), and creativity (zero existing RL benchmarks cover investigative epidemiology). Below is the exhaustive analysis of the top 5 ideas, followed by the definitive #1 recommendation with full implementation spec.

---

## Why the "investigation metaphor" dominates this hackathon

The single most important design insight for OpenEnv environments targeting LLM agents is the **investigation metaphor**: the agent investigates a scenario with hidden ground truth by sequentially requesting evidence, forming hypotheses, and converging on an answer. This pattern outperforms all alternatives because it creates genuine information-gating (the agent must decide what to examine next), enables deterministic grading (planted answers are verifiable), produces dense reward (each evidence request narrows or expands the search), and plays directly to LLM strengths (reading text, reasoning about patterns, applying domain knowledge).

All 800+ existing OpenEnv submissions cluster in saturated areas — **SQL generation, email triage, code review, contract analysis, and games**. The SF hackathon gallery shows additional entries in sports strategy, agriculture, debugging, and music. No submissions exist in public health, financial forensics, food safety, or clinical pharmacy. This means every idea below occupies greenfield territory where novelty points are essentially free.

The community gap analysis confirms this opportunity: IBM's survey of 120 agent benchmarks found healthcare, finance, and professional investigation workflows are the most underserved domains. Frontier labs are reportedly paying **$20K–$300K per environment** for enterprise-grade RL environments, and the Epoch AI FAQ specifically calls out long-horizon investigation tasks as "the future direction."

---

## Idea #1: EpiDetective — Disease outbreak investigation

**Domain:** Public health epidemiology | **Build difficulty:** 3–4 days | **Novelty:** ★★★★★

This environment simulates the CDC's canonical 13-step outbreak investigation workflow. The agent receives an initial alert (e.g., "cluster of 47 gastroenteritis cases reported from a county fair"), then must strategically request evidence — line lists, lab results, exposure histories, epi curves, environmental samples — to identify the pathogen, contamination source, and transmission route. Each scenario has planted ground truth, enabling fully deterministic grading.

**Why it scores highest on real-world utility (30%):** Outbreak investigation is a genuine professional task performed thousands of times yearly by epidemiologists at CDC, state health departments, and WHO. The CDC teaches it as a structured 13-step process, with published MMWR case reports providing abundant realistic templates. The environment directly models how public health professionals work, and post-COVID, every judge will immediately grasp the stakes.

**Three tasks with grader logic:**

Task 1 — **Point-source foodborne outbreak** (Easy). A wedding reception with **50 attendees**, 18 ill. Single pathogen (Salmonella), single food source (potato salad), classic epi curve shape. Agent has ~15 actions to identify pathogen + source + route. Grader: `0.25` for correct pathogen (exact match from synonym set), `0.25` for correct food vehicle, `0.20` for correct transmission route (categorical: foodborne/waterborne/airborne/person-to-person), `0.15` for reasonable case definition (checklist: includes person/place/time criteria), `0.15` for investigation efficiency (actions used / optimal actions, inverted and clamped). Total: 0.0–1.0.

Task 2 — **Community respiratory outbreak** (Medium). A cluster of **120+ cases** across three schools and a nursing home. Pathogen is Legionella from a contaminated cooling tower. Confounders: concurrent influenza season creates noise in case data. Agent must distinguish Legionella cases from flu, identify the common environmental exposure, and trace to the cooling tower. More data sources to query, red herring exposures, temporal overlap with background illness. Same grading rubric, but the statistical signal-to-noise ratio is lower.

Task 3 — **Multi-source, multi-pathogen investigation** (Hard). **200+ cases** across a metro area that appear to be one outbreak but are actually two distinct outbreaks overlapping in time and geography — e.g., E. coli from contaminated lettuce at grocery chain A AND Norovirus from an infected food handler at restaurant chain B. Agent must correctly differentiate the two outbreaks, identify both pathogens, both sources, and both transmission routes. Grader uses precision/recall over outbreak assignment (`0.30`), plus per-outbreak pathogen/source identification (`0.35` each for the two outbreaks), normalized to 0.0–1.0.

**Action/observation space:**

```
Actions (text commands):
- view_initial_alert()           → outbreak notification text
- request_line_list()            → case demographics, onset dates, symptoms
- generate_epi_curve(grouping)   → temporal case distribution  
- request_lab_results(case_ids)  → pathogen identification for specific cases
- get_exposure_history(case_ids) → food/location/contact exposures
- calculate_attack_rate(item)    → ate-ill / ate-well rates for a food item
- calculate_odds_ratio(exposure) → statistical association measure
- request_environmental_samples(location) → environmental test results
- submit_hypothesis(pathogen, source, route) → partial feedback
- submit_final_answer(...)       → triggers grading

Observations: JSON with structured data + natural language narrative
State: episode_id, step_count, queries_made, data_unlocked
```

**Reward function:** Dense, multi-signal. Each `submit_hypothesis` call returns partial score against ground truth components. Each data request that narrows the investigation (high information gain) yields a small positive signal. Redundant or irrelevant queries yield zero. Final score is the component-wise grading rubric above. This ensures the agent receives feedback at every step, not just at the end.

**Why a Nemotron-class LLM makes meaningful progress:** LLMs achieve **>80% accuracy on medical diagnostic reasoning** tasks (JAMIA Open, 2025). The structured action space maps directly to tool-calling patterns LLMs excel at. Simpler scenarios (Task 1) involve straightforward pattern matching — high attack rates for a specific food, matching symptoms to known pathogens — well within Nemotron's capabilities. Task 3 requires sophisticated multi-hypothesis reasoning that would challenge even frontier models, creating the differentiation the hackathon needs.

**Feasibility:** Pure Python, no external dependencies. Scenarios stored as JSON templates (~KB each). Memory usage under **100MB**. The CDC's MMWR reports provide 30+ real outbreak templates to adapt. All computations (attack rates, odds ratios) are simple arithmetic. Inference easily completes in under 20 minutes.

---

## Idea #2: AuditTrail — Forensic financial investigation

**Domain:** Accounting/audit forensics | **Build difficulty:** 4–5 days | **Novelty:** ★★★★★

The agent receives a flagged financial anomaly and must investigate by querying ledger entries, requesting supporting documents, cross-referencing vendor records, and following money flows to classify anomalies as errors, fraud, or legitimate transactions.

**Real-world utility:** The global audit industry exceeds **$250 billion annually**. Financial fraud causes $4.7 trillion in losses per year (ACFE). TheAgentCompany benchmark found finance tasks have among the *lowest* agent success rates, confirming this is both important and challenging. No existing benchmark covers sequential forensic investigation.

**Three tasks:** (1) *Duplicate payment detection* — 500+ AP entries, 5 planted duplicates with varying sophistication (exact duplicates → near-duplicates with altered vendor names). Grader: precision × recall over identified duplicates. (2) *Revenue recognition fraud* — quarterly entries with fictitious revenue, channel stuffing, or premature recognition. Grader: 0.3 correct entries + 0.3 fraud type + 0.2 responsible party + 0.2 accounting standard violated. (3) *Related-party transaction discovery* — hidden relationships between vendors and officers revealed through cross-referencing addresses, ownership records, and transaction patterns. Grader: F1 over discovered links × classification correctness.

**Why it's strong:** Crystal-clear deterministic ground truth (planted anomalies). Natural investigation workflow (query → hypothesize → verify). Text-heavy domain where LLMs shine. Generates via synthetic data using `Faker` + custom financial templates.

**Why it's #2 not #1:** Audit investigation workflows are less standardized than CDC's 13-step process, making the action space slightly harder to design cleanly. Financial domain knowledge is deeper and more specialized. Grading "correct reasoning chain" is harder than grading "correct pathogen."

---

## Idea #3: SafetyInspector — Food safety inspection prioritization

**Domain:** Food safety regulation | **Build difficulty:** 3–4 days | **Novelty:** ★★★★★

A food safety regulator manages inspection resources across a portfolio of facilities. Each simulated week, the agent receives complaint data, lab results, and risk profiles, then decides which facilities to inspect, what inspection type to conduct, and whether to issue recalls.

**Real-world utility:** The FDA oversees **77,000+ food facilities**. Foodborne illness causes 48 million cases, 128,000 hospitalizations, and 3,000 deaths annually in the US alone. Risk-based inspection scheduling is an active area of regulatory science with no existing RL benchmark.

**Three tasks:** (1) *Single-category inspection scheduling* — 20 facilities, 2 inspectors, single product category, 12-week horizon. Grader: contamination detection rate × (1 − false positive rate). (2) *Multi-facility outbreak containment* — 80 facilities with supply chain links, hidden contamination spreading through shared suppliers, budget constraints. Grader: outbreaks prevented + public health impact + cost efficiency. (3) *Emerging pathogen scenario* — 200 facilities, import/export dynamics, emerging pathogen with novel characteristics, political pressure against closures. Grader: disability-adjusted life years prevented + economic impact + compliance score.

**Why it's #3:** Completely uncharted territory (zero RL environments exist). Clean sequential structure. But slightly less "detective-story compelling" than epidemiology — the agent manages a portfolio rather than solving a mystery, which produces slightly weaker narrative engagement for judges.

---

## Idea #4: PharmCheck — Clinical medication review

**Domain:** Clinical pharmacy | **Build difficulty:** 4–5 days | **Novelty:** ★★★★★

The agent performs a clinical pharmacist's medication review: checking a patient's medication list for drug-drug interactions, contraindications, dosage errors, therapeutic duplications, and prescribing cascades.

**Real-world utility:** Adverse drug events cause **1.3 million emergency visits annually** in the US. Polypharmacy management is a critical and growing challenge as populations age. While drug interaction *databases* exist (DrugBank, Micromedex), no benchmark tests the sequential *decision workflow* of a clinical pharmacist.

**Three tasks:** (1) *Polypharmacy interaction screen* — patient on 8+ medications, 3 planted clinically significant interactions. Grader: recall × severity classification accuracy × alternative recommendation quality. (2) *Renal dosage adjustment* — CKD patient requiring dose modifications for 6 medications. Grader: medication identification (precision/recall) × dose accuracy (within 10% = full, within 25% = half). (3) *Prescribing cascade detection* — medication list containing a cascade where Drug A's side effect is treated by Drug B whose side effect is treated by Drug C. Grader: duplication detection (0.4) + cascade identification (0.4) + deprescribing recommendation (0.2).

**Why it's #4:** Extremely clean grading against pharmacological ground truth. Safety-critical domain. But the task is more "lookup and verify" than "investigate and discover" — each step has less strategic depth than outbreak investigation. Risk of feeling like a sophisticated database query rather than genuine sequential decision-making.

---

## Idea #5: PortOps — Maritime port orchestration

**Domain:** Maritime logistics | **Build difficulty:** 5–6 days | **Novelty:** ★★★★☆

A container terminal operations manager assigns berths to arriving vessels, allocates quay cranes, manages yard storage, and handles disruptions (equipment breakdowns, weather, priority cargo). **80% of global trade moves by sea**, making this a $14 trillion logistics domain.

**Three tasks:** (1) *Basic berth assignment* — 3 berths, 4 cranes, 5 vessels over 24 hours. Grader: average vessel turnaround time. (2) *Multi-resource coordination* — 6 berths, 10 cranes, 15 vessels with equipment breakdowns and tide restrictions. Grader: weighted delay + utilization + congestion. (3) *Full-scale operations* — 10 berths, 15 cranes, 30 vessels over 7 days with weather, labor shifts, and cascading delays. Grader: composite throughput, cost, and efficiency score.

**Why it's #5:** Exotic domain with high wow-factor — judges rarely see maritime environments. Rich multi-step optimization. But it's more of a scheduling/optimization problem than an investigation, which means traditional optimization algorithms might outperform LLMs. Also the most complex to implement, requiring a discrete-event port simulation engine.

---

## How the top 5 compare on every judging criterion

| Criterion (weight) | EpiDetective | AuditTrail | SafetyInspector | PharmCheck | PortOps |
|---|---|---|---|---|---|
| **Real-world utility** (30%) | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★★★ | ★★★★☆ |
| **Task & grader quality** (25%) | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★★☆ |
| **Environment design** (20%) | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★☆ | ★★★★★ |
| **Code quality/spec** (15%) | ★★★★★ | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| **Creativity & novelty** (10%) | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★★★ |
| **Build feasibility** (1 week) | ★★★★★ | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| **LLM agent solvability** | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★★★ | ★★★☆☆ |
| **Weighted total** | **4.95** | **4.45** | **4.35** | **4.50** | **4.05** |

---

## The definitive recommendation: build EpiDetective

**EpiDetective wins on every dimension that matters.** It has the cleanest mapping between a real professional workflow (CDC's 13-step outbreak investigation) and the OpenEnv step/reset/state API. It produces the most naturally dense reward signal — every evidence request is either informative or wasteful, every hypothesis is partially scorable. Its grading is fully deterministic against planted ground truth with no subjective judgment required. The domain is universally understood post-COVID, creating instant judge engagement. And critically, it sits in the sweet spot for Nemotron-class LLMs: Task 1 is solvable through straightforward pattern matching and domain knowledge, Task 2 requires distinguishing signal from noise, and Task 3 demands multi-hypothesis reasoning that would challenge frontier models.

The implementation is also the lightest of all five options. Scenario generation requires only template-based JSON with parameterized randomization — no external databases, no simulation engines, no heavy dependencies. The entire environment runs in under **100MB of RAM**. A functional prototype can be built in **2–3 days**, leaving time for polishing the Gradio web interface, writing excellent documentation, and tuning the difficulty curve.

**The one risk to mitigate:** Ensure Task 1 isn't *too* easy (trivially solvable by keyword matching without real reasoning). Add at least 2–3 red herring exposures with plausible but non-significant attack rates, and require the agent to demonstrate statistical reasoning (comparing attack rates across exposures) rather than just identifying the most-mentioned food item.

Build this environment. It will stand out from the 800+ SQL generators and email triagers, impress Meta engineers with its real-world utility and clean design, and give the Nemotron evaluation agent a genuinely interesting problem to solve.