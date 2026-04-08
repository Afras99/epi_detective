# Task Specifications & Grader Logic

## Task 1: Point-Source Foodborne Outbreak (Easy)

### Scenario template

```
Setting: Shared meal event (wedding, potluck, company picnic, birthday party)
Attendees: 30-80 people
Ill: 10-30 (attack rate 30-60% among those who ate the guilty food)
Pathogen pool: S. aureus, C. perfringens, Salmonella, Norovirus, E. coli O157:H7
Food vehicles served: 5-8 items
Red herring foods: 2-3 (foods with plausible but non-significant attack rates)
Max steps: 15
Optimal steps: 8
Confounders: NONE (no background illness, no multiple events, no delayed reporting)
```

### What the agent receives at reset

A narrative alert like:
> "The county health department received reports of 23 people experiencing gastrointestinal illness following a church potluck held on Saturday evening, March 15th. Approximately 65 people attended the event. Symptoms reported include nausea, vomiting, and abdominal cramps, with onset times ranging from 2 to 8 hours after the meal. Two individuals were evaluated at the emergency department. No hospitalizations or deaths have been reported. An investigation has been initiated."

### Evidence available (gated by actions)

| Action | Returns | Information value |
|--------|---------|-------------------|
| `request_line_list()` | Table: case_id, name, age, sex, onset_datetime, symptoms[], hospitalized, lab_confirmed | High — establishes scope |
| `generate_epi_curve(grouping="hour")` | Histogram of case onsets by hour — reveals incubation pattern | Medium — narrows pathogen type |
| `get_exposure_history(case_ids=[...])` | For each case: list of foods eaten, locations visited | High — enables attack rate calc |
| `calculate_attack_rate(food_item="potato_salad")` | `{"ate_ill": 20, "ate_well": 2, "not_ate_ill": 3, "not_ate_well": 40, "attack_rate_ate": 0.91, "attack_rate_not_ate": 0.07, "relative_risk": 13.0}` | Very high — statistical evidence |
| `request_lab_results(case_ids=[...])` | Pathogen identification from clinical specimens | Very high — confirms etiology |
| `request_environmental_samples(location="kitchen")` | Food samples, swab results from preparation areas | Medium — confirms source |
| `submit_hypothesis(pathogen, source, route)` | Partial score feedback (0.0-1.0) | Meta — lets agent test theories |
| `submit_final_answer(pathogen, source, route, case_definition)` | Final graded score | Terminal |

### Red herring design (CRITICAL for preventing trivial solutions)

The scenario generator MUST include 2-3 foods with plausible but non-significant attack rates:

```
Example good red herring setup:
- Potato salad (GUILTY):     attack_rate_ate=0.78, attack_rate_not_ate=0.08, RR=9.75
- Coleslaw (RED HERRING):    attack_rate_ate=0.35, attack_rate_not_ate=0.28, RR=1.25
- Fried chicken (RED HERRING): attack_rate_ate=0.45, attack_rate_not_ate=0.20, RR=2.25
- Cornbread (NEUTRAL):       attack_rate_ate=0.30, attack_rate_not_ate=0.32, RR=0.94

The agent must compare ALL attack rates, not just pick the first food with any association.
Fried chicken looks suspicious (RR=2.25) until you see potato salad (RR=9.75).
```

### Grading formula

```python
score = (
    0.25 * pathogen_match(submitted, ground_truth)     # 0.0 or 0.5 or 1.0
  + 0.25 * source_match(submitted, ground_truth)        # 0.0 or 0.5 or 1.0
  + 0.20 * route_match(submitted, ground_truth)         # 0.0 or 1.0
  + 0.15 * case_definition_quality(submitted)           # 0.0 to 1.0
  + 0.15 * efficiency_score(steps_taken, optimal=8, max=15)  # 0.0 to 1.0
)
```

**Pathogen match:**
- Exact match (including synonyms): 1.0
- Partial match (correct genus, missing/wrong species): 0.5
- No match: 0.0

**Source match:**
- Exact match (including synonyms like "potato salad" = "potato-salad" = "potatoes"): 1.0
- Partial (correct food category, e.g., "salad" when answer is "potato_salad"): 0.5
- No match: 0.0

**Route match:**
- Exact: 1.0 (categories: foodborne, waterborne, airborne, person-to-person, environmental)
- No match: 0.0

**Case definition quality:**
Check for three components (person/place/time criteria per CDC guidelines):
- Has clinical criteria (symptoms): +0.40
- Has time criteria (onset window): +0.30
- Has place/exposure criteria: +0.30

**Efficiency:**
```python
if steps_taken <= 8: return 1.0
if steps_taken >= 15: return 0.0
return 1.0 - (steps_taken - 8) / (15 - 8)
```

---

## Task 2: Community Respiratory Outbreak (Medium)

### Scenario template

```
Setting: Multiple locations in a community (3 schools + 1 nursing home)
Cases: 120+ total
True outbreak: Legionella from a contaminated cooling tower (affecting all locations)
Background noise: Concurrent influenza season (30-50 additional flu cases mixed in)
Pathogen: Legionella pneumophila
Source: Cooling tower at a commercial building (shared air exposure across locations)
Max steps: 25
Optimal steps: 14
Confounders:
  - Background influenza cases that overlap in time and geography
  - Some locations share a food vendor (red herring)
  - Varying onset times due to Legionella's 2-10 day incubation
```

### Key design: Signal vs. noise

The medium difficulty comes from the agent needing to **distinguish Legionella from influenza**:

| Feature | Legionella cases | Influenza cases |
|---------|-----------------|-----------------|
| Pneumonia | YES (key differentiator) | Usually no (upper respiratory) |
| Fever | Very high (>39°C) | High |
| Cough | Yes (productive) | Yes (dry initially) |
| GI symptoms | Sometimes | Rarely |
| Muscle aches | Yes | Yes |
| Age distribution | Older adults, smokers | All ages |
| Lab results | Urinary antigen positive | Flu rapid test positive |
| Exposure link | Proximity to cooling tower | Close contact with sick persons |

The agent must:
1. Recognize that pneumonia cases cluster differently from non-pneumonia cases
2. Request lab results to separate Legionella from influenza
3. Map cases geographically to identify the cooling tower exposure
4. Request environmental samples from the cooling tower

### Additional red herrings for Task 2

- School cafeteria food (all schools use same vendor) — looks like foodborne initially
- Shared school bus routes — looks like person-to-person
- A construction site near the schools — irrelevant but plausible

### Grading formula

Same structure but grading ALSO penalizes for misidentifying flu cases as outbreak cases:

```python
score = (
    0.20 * pathogen_match(submitted, "legionella")
  + 0.20 * source_match(submitted, "cooling_tower")
  + 0.15 * route_match(submitted, "environmental_airborne")
  + 0.15 * case_definition_quality(submitted)
  + 0.15 * case_differentiation_score(submitted_case_list, ground_truth_split)
  + 0.15 * efficiency_score(steps_taken, optimal=14, max=25)
)
```

**Case differentiation score** (new for Task 2):
```python
# Did the agent correctly identify which cases are Legionella vs flu?
# Measured by precision and recall on case assignment
precision = true_legionella_identified / total_identified_as_legionella
recall = true_legionella_identified / actual_legionella_cases
return 2 * (precision * recall) / (precision + recall)  # F1 score
```

---

## Task 3: Multi-Source Overlapping Outbreaks (Hard)

### Scenario template

```
Setting: Metropolitan area — multiple restaurants and a grocery chain
Cases: 200+ across the metro
TRUE OUTBREAKS (two simultaneous):
  Outbreak A: E. coli O157:H7 from contaminated romaine lettuce at Grocery Chain X
  Outbreak B: Norovirus from an infected food handler at Restaurant Chain Y
Geographic overlap: YES — some patients visited both establishments
Temporal overlap: YES — both outbreaks started within 3 days of each other
Max steps: 35
Optimal steps: 20
Confounders:
  - Cases appear to be one large outbreak on initial line list
  - Some patients have overlapping symptom profiles
  - Geographic clustering looks like a single source
  - Lab results are the key to separation (different pathogens)
```

### What makes Task 3genuinely hard

1. **The agent must HYPOTHESIZE there are two outbreaks** — the initial data doesn't make this obvious
2. **Symptom overlap**: Both cause diarrhea, abdominal cramps. But E. coli → bloody diarrhea, no/low fever. Norovirus → vomiting dominant, some fever.
3. **Lab subtyping is critical**: E. coli and Norovirus have completely different lab results. Agent must request labs for multiple case subsets.
4. **Statistical analysis**: Attack rates must be calculated SEPARATELY for each suspected cluster. Mixed analysis gives confusing results.

### Progression a good agent would follow

1. Request line list → see 200+ cases, looks overwhelming
2. Generate epi curve → see a BIMODAL or unusually wide curve (hint: two overlapping peaks)
3. Request lab results for a sample → discover BOTH E. coli and Norovirus
4. Realize there are TWO outbreaks → split cases by lab results
5. Get exposure histories for each group separately
6. Calculate attack rates within each group → identify the sources
7. Submit both outbreaks

### Grading formula

```python
# First: grade the cluster separation (precision/recall)
cluster_score = f1_score(
    submitted_cluster_A_cases, 
    ground_truth_outbreak_A_cases
) * 0.5 + f1_score(
    submitted_cluster_B_cases, 
    ground_truth_outbreak_B_cases
) * 0.5

# Then: grade each outbreak separately
outbreak_A_score = (
    0.30 * pathogen_match(submitted_A, "e_coli_o157")
  + 0.30 * source_match(submitted_A, "romaine_lettuce")
  + 0.20 * route_match(submitted_A, "foodborne")
  + 0.20 * case_definition_quality(submitted_A)
)

outbreak_B_score = (
    0.30 * pathogen_match(submitted_B, "norovirus")
  + 0.30 * source_match(submitted_B, "restaurant_chain_y_food_handler")
  + 0.20 * route_match(submitted_B, "foodborne_person_to_person")
  + 0.20 * case_definition_quality(submitted_B)
)

# Final score
score = (
    0.30 * cluster_score
  + 0.30 * outbreak_A_score
  + 0.30 * outbreak_B_score
  + 0.10 * efficiency_score(steps_taken, optimal=20, max=35)
)
```

### Partial credit scenarios for Task 3

| Agent behavior | Score range |
|---------------|-------------|
| Identifies both pathogens + both sources correctly | 0.85-1.0 |
| Identifies both pathogens, one source correct | 0.60-0.75 |
| Identifies only ONE outbreak correctly, misses the other | 0.35-0.50 |
| Treats everything as a single outbreak, picks the dominant pathogen | 0.15-0.30 |
| Completely wrong on everything | 0.0-0.10 |

---

## Dense reward function (all tasks)

```python
def compute_step_reward(action, state, ground_truth):
    """
    Every step produces a reward signal. No sparse rewards.
    
    Philosophy:
    - Gathering relevant evidence = small positive reward
    - Redundant queries = small negative (penalize waste)
    - Hypothesis testing = scaled partial feedback
    - Final submission = full grading
    """
    
    # Already queried this exact action+params before?
    action_key = f"{action.command}:{json.dumps(action.parameters, sort_keys=True)}"
    if action_key in state.action_history:
        return -0.02  # Redundant query penalty
    
    # Mark as queried
    state.action_history.add(action_key)
    
    # Evidence gathering rewards (proportional to information value)
    EVIDENCE_REWARDS = {
        "request_line_list": 0.05,          # Always useful first step
        "generate_epi_curve": 0.03,         # Helpful but not critical
        "get_exposure_history": 0.05,       # Key for source identification
        "request_lab_results": 0.08,        # Highest value — identifies pathogen
        "calculate_attack_rate": 0.05,      # Statistical evidence for source
        "calculate_odds_ratio": 0.04,       # Additional statistical support
        "request_environmental_samples": 0.06,  # Confirms source
    }
    
    if action.command in EVIDENCE_REWARDS:
        base_reward = EVIDENCE_REWARDS[action.command]
        
        # Bonus: if this is a particularly informative query
        # e.g., calculating attack rate for the CORRECT food
        if action.command == "calculate_attack_rate":
            if action.parameters.get("food_item") == ground_truth["source"]:
                base_reward += 0.05  # Bonus for investigating the right food
        
        return base_reward
    
    # Hypothesis testing: partial feedback
    if action.command == "submit_hypothesis":
        partial = partial_grade(action.parameters, ground_truth)
        return partial * 0.10  # Scale down to avoid gaming
    
    # Final answer: full grading
    if action.command == "submit_final_answer":
        return full_grade(action.parameters, ground_truth, state)
    
    # Unknown command
    return -0.01

def partial_grade(hypothesis, ground_truth):
    """Quick partial score for hypothesis testing."""
    score = 0.0
    if fuzzy_match(hypothesis.get("pathogen", ""), ground_truth["pathogen"], ground_truth["pathogen_synonyms"]):
        score += 0.4
    if fuzzy_match(hypothesis.get("source", ""), ground_truth["source"], ground_truth["source_synonyms"]):
        score += 0.4
    if hypothesis.get("route", "").lower() == ground_truth["route"].lower():
        score += 0.2
    return score
```

---

## Nemotron/LLM agent solvability analysis

### Task 1 (Easy) — Expected Nemotron score: 0.60-0.85

A competent LLM should:
- Understand the investigation workflow (trained on CDC literature)
- Request line list and lab results systematically
- Calculate attack rates for multiple foods
- Compare relative risks to identify the guilty food
- Identify the pathogen from lab results

Where it might struggle:
- Inefficiency (too many steps) → loses efficiency points
- Not recognizing synonym variations for pathogen names
- Skipping case definition (loses 0.15)

### Task 2 (Medium) — Expected Nemotron score: 0.35-0.60

A competent LLM should:
- Recognize respiratory symptoms as different from typical foodborne
- Request lab results to differentiate Legionella from flu
- Investigate environmental sources once Legionella is identified

Where it might struggle:
- Initially treating everything as one outbreak
- Not distinguishing pneumonia cases from upper respiratory cases
- Missing the cooling tower as the source (requires environmental thinking)

### Task 3 (Hard) — Expected Nemotron score: 0.15-0.40

This is designed to challenge frontier models:
- Recognizing two overlapping outbreaks requires sophisticated reasoning
- Statistical analysis must be done per-cluster, not overall
- Agent must manage a larger investigation with more decision points

Even partial progress (identifying one outbreak correctly) yields meaningful scores.
