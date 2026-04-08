# Scenario Generator & Evidence Engine Design

## Scenario generation pipeline

```
Template selection → Pathogen sampling → Setting + food vehicle selection
→ Population generation → Exposure matrix → Case generation (ill + well)
→ Onset time distribution → Symptom assignment → Lab result generation
→ Evidence layer construction → Ground truth packaging → scenario.json
```

## Step-by-step scenario construction

### Step 1: Template + random seed

Every scenario is **fully deterministic** given a seed. This is critical for reproducibility.

```python
def generate_scenario(task_id: str, seed: int) -> Scenario:
    rng = random.Random(seed)
    template = load_template(task_id)  # point_source / respiratory / multi_outbreak
```

### Step 2: Sample pathogen and food vehicle

```python
# Pick pathogen from task-appropriate pool
pathogen_key = rng.choice(template["pathogen_pool"])
pathogen = PATHOGENS[pathogen_key]

# Pick a food vehicle associated with this pathogen
food_vehicle = rng.choice(pathogen["common_foods"])

# Pick setting
setting_key = rng.choice(template["setting_pool"])
setting = SETTINGS[setting_key]
```

### Step 3: Generate the population

```python
n_attendees = rng.randint(*template["num_attendees"])
n_ill = rng.randint(*template["num_ill"])
n_well = n_attendees - n_ill

# Generate demographics using Faker
people = []
for i in range(n_attendees):
    person = {
        "case_id": f"c{i:03d}",
        "name": fake.name(),
        "age": sample_age(pathogen.get("age_vulnerability", []), rng),
        "sex": rng.choice(["M", "F"]),
        "is_ill": i < n_ill,  # First n_ill are cases
    }
    people.append(person)
rng.shuffle(people)  # Randomize order so ill aren't always first
```

### Step 4: Build exposure matrix

This is the most important data structure. It determines who ate what, and ensures the guilty food has a statistically significant association with illness.

```python
def build_exposure_matrix(people, guilty_food, all_foods, red_herring_foods, rng):
    """
    For each person, generate which foods they ate.
    
    Key constraints:
    - Guilty food: ~75-90% of ILL people ate it, ~20-40% of WELL people ate it
    - Red herring foods: ~50-65% of ILL ate it, ~40-55% of WELL ate it
    - Neutral foods: ~40-60% of ALL people ate it (no illness correlation)
    """
    matrix = {}
    
    for person in people:
        exposures = {}
        for food in all_foods:
            if food == guilty_food:
                if person["is_ill"]:
                    exposures[food] = rng.random() < rng.uniform(0.75, 0.90)
                else:
                    exposures[food] = rng.random() < rng.uniform(0.15, 0.35)
            elif food in red_herring_foods:
                if person["is_ill"]:
                    exposures[food] = rng.random() < rng.uniform(0.50, 0.65)
                else:
                    exposures[food] = rng.random() < rng.uniform(0.40, 0.55)
            else:
                exposures[food] = rng.random() < rng.uniform(0.35, 0.60)
        
        # Ensure at least SOME ill people who didn't eat the guilty food
        # (realistic — some cases are false positives or secondary transmission)
        matrix[person["case_id"]] = exposures
    
    return matrix
```

### Step 5: Generate onset times

Onset times follow the pathogen's incubation distribution, anchored to the event time.

```python
def generate_onset_times(ill_people, pathogen, event_datetime, rng):
    """
    Generate realistic onset times using log-normal distribution
    (matches observed outbreak incubation period distributions).
    """
    median_hours = pathogen["incubation_hours"]["median"]
    # Log-normal parameters derived from median and range
    mu = math.log(median_hours)
    sigma = 0.4  # Produces reasonable spread
    
    for person in ill_people:
        incubation_hours = rng.lognormvariate(mu, sigma)
        # Clamp to realistic range
        min_h, max_h = pathogen["incubation_hours"].get("range", [median_hours*0.3, median_hours*3])
        incubation_hours = max(min_h, min(max_h, incubation_hours))
        
        person["onset_datetime"] = event_datetime + timedelta(hours=incubation_hours)
```

### Step 6: Assign symptoms

```python
def assign_symptoms(person, pathogen, rng):
    """Assign symptoms based on pathogen-specific frequency data."""
    symptoms = []
    for symptom, probability in pathogen["symptoms"]["frequency"].items():
        if rng.random() < probability:
            symptoms.append(symptom)
    
    # Ensure at least one primary symptom (unrealistic if a case has NO symptoms)
    if not symptoms:
        symptoms.append(rng.choice(pathogen["symptoms"]["primary"]))
    
    person["symptoms"] = symptoms
    person["hospitalized"] = rng.random() < 0.08
    person["lab_confirmed"] = rng.random() < 0.65
```

### Step 7: Generate lab results

```python
def generate_lab_results(people, pathogen, rng):
    """
    Lab results are gated — agent must request them.
    Only lab-confirmed cases return positive results.
    """
    results = {}
    for person in people:
        if person.get("is_ill") and person.get("lab_confirmed"):
            results[person["case_id"]] = {
                "specimen_type": "stool" if pathogen["type"] != "respiratory" else "respiratory",
                "test_method": pathogen["lab_confirmation"].split(" ")[0],
                "result": "POSITIVE",
                "organism": pathogen["full_name"],
                "serotype": rng.choice(pathogen.get("common_serotypes", [""])),
                "collection_date": person["onset_datetime"] + timedelta(days=rng.randint(1, 3))
            }
        elif person.get("is_ill"):
            results[person["case_id"]] = {
                "specimen_type": "stool",
                "test_method": "Culture",
                "result": "PENDING",
                "organism": None,
                "note": "Specimen collected, awaiting results"
            }
    return results
```

### Step 8: Build evidence layers

```python
def build_evidence_layers(people, exposure_matrix, lab_results, 
                          setting, pathogen, event_datetime):
    """
    Package all data into gated evidence layers.
    The agent unlocks each layer by taking the corresponding action.
    """
    return {
        "initial_alert": {
            "narrative": generate_alert_narrative(setting, people, event_datetime),
            "available_at": "reset"
        },
        "line_list": {
            "data": [
                {
                    "case_id": p["case_id"],
                    "name": p["name"],
                    "age": p["age"],
                    "sex": p["sex"],
                    "onset_datetime": p["onset_datetime"].isoformat() if p.get("onset_datetime") else None,
                    "symptoms": p.get("symptoms", []),
                    "hospitalized": p.get("hospitalized", False),
                }
                for p in people if p["is_ill"]
            ],
            "gated_by": "request_line_list"
        },
        "epi_curve_data": {
            "onset_times": [p["onset_datetime"].isoformat() for p in people if p.get("onset_datetime")],
            "gated_by": "generate_epi_curve"
        },
        "exposure_histories": {
            "data": exposure_matrix,
            "gated_by": "get_exposure_history"
        },
        "lab_results": {
            "data": lab_results,
            "gated_by": "request_lab_results"
        },
        "environmental_samples": {
            "data": generate_environmental_results(setting, pathogen),
            "gated_by": "request_environmental_samples"
        }
    }
```

---

## Evidence engine (information gating)

The evidence engine is what makes this a **genuine sequential decision problem**. The agent cannot see all data at once — it must choose what to investigate.

### Action → evidence mapping

```python
class EvidenceEngine:
    def __init__(self, scenario):
        self.scenario = scenario
        self.unlocked = {"initial_alert"}
        self.query_log = []
    
    def process_action(self, action: EpiAction) -> EpiObservation:
        """Process an agent action and return the appropriate observation."""
        
        command = action.command
        params = action.parameters
        
        if command == "view_initial_alert":
            return self._return_alert()
        
        elif command == "request_line_list":
            self.unlocked.add("line_list")
            return self._return_line_list()
        
        elif command == "generate_epi_curve":
            self.unlocked.add("epi_curve")
            grouping = params.get("grouping", "hour")
            return self._return_epi_curve(grouping)
        
        elif command == "get_exposure_history":
            self.unlocked.add("exposure_histories")
            case_ids = params.get("case_ids", [])
            # Can request for specific cases or all cases
            if not case_ids:
                case_ids = [c["case_id"] for c in self.scenario.evidence["line_list"]["data"]]
            return self._return_exposures(case_ids)
        
        elif command == "request_lab_results":
            self.unlocked.add("lab_results")
            case_ids = params.get("case_ids", [])
            return self._return_lab_results(case_ids)
        
        elif command == "calculate_attack_rate":
            food_item = params.get("food_item", "")
            return self._calculate_attack_rate(food_item)
        
        elif command == "calculate_odds_ratio":
            exposure = params.get("exposure", "")
            return self._calculate_odds_ratio(exposure)
        
        elif command == "request_environmental_samples":
            location = params.get("location", "")
            self.unlocked.add("environmental_samples")
            return self._return_environmental(location)
        
        elif command == "submit_hypothesis":
            return self._evaluate_hypothesis(params)
        
        elif command == "submit_final_answer":
            return self._grade_final(params)
        
        else:
            return EpiObservation(
                result_type="error",
                data={},
                narrative=f"Unknown command: {command}. Available: {self._available_actions()}",
                available_actions=self._available_actions(),
                step_reward=-0.01
            )
    
    def _calculate_attack_rate(self, food_item):
        """Compute 2x2 table for a specific food item."""
        exposures = self.scenario.evidence["exposure_histories"]["data"]
        cases = {c["case_id"] for c in self.scenario.evidence["line_list"]["data"]}
        
        ate_ill = ate_well = not_ate_ill = not_ate_well = 0
        
        for case_id, foods in exposures.items():
            ate = foods.get(food_item, False)
            ill = case_id in cases
            
            if ate and ill: ate_ill += 1
            elif ate and not ill: ate_well += 1
            elif not ate and ill: not_ate_ill += 1
            else: not_ate_well += 1
        
        ar_ate = ate_ill / (ate_ill + ate_well) if (ate_ill + ate_well) > 0 else 0
        ar_not = not_ate_ill / (not_ate_ill + not_ate_well) if (not_ate_ill + not_ate_well) > 0 else 0
        rr = ar_ate / ar_not if ar_not > 0 else float('inf')
        
        return EpiObservation(
            result_type="attack_rate",
            data={
                "food_item": food_item,
                "ate_ill": ate_ill,
                "ate_well": ate_well,
                "not_ate_ill": not_ate_ill,
                "not_ate_well": not_ate_well,
                "attack_rate_ate": round(ar_ate, 3),
                "attack_rate_not_ate": round(ar_not, 3),
                "relative_risk": round(rr, 2)
            },
            narrative=f"Attack rate analysis for {food_item}: "
                      f"{ar_ate:.1%} of those who ate it became ill vs "
                      f"{ar_not:.1%} of those who did not (RR={rr:.1f}).",
            available_actions=self._available_actions(),
            step_reward=self._compute_reward("calculate_attack_rate", {"food_item": food_item})
        )
```

---

## Alert narrative generation

The initial alert is the only thing the agent sees at `reset()`. It must be realistic and information-gated.

```python
ALERT_TEMPLATES = {
    "point_source": [
        "The {county} health department received reports of {n_ill} people experiencing "
        "{primary_symptom_group} following a {setting_name} held on {event_date}. "
        "Approximately {n_attendees} people attended the event. Symptoms reported include "
        "{symptom_list}, with onset times ranging from {onset_range}. "
        "{hospital_text} An investigation has been initiated.",
        
        "A cluster of {n_ill} gastrointestinal illness cases has been reported to "
        "the local health department. All cases attended a {setting_name} on {event_date} "
        "at {venue_name}. Common symptoms include {symptom_list}. "
        "Onset times suggest an incubation period of {incubation_range}. "
        "{hospital_text}"
    ],
    "respiratory": [
        "The state health department has been notified of an unusual cluster of "
        "pneumonia cases across multiple facilities in {metro_area}. Over the past "
        "{days_span} days, {n_ill} cases of pneumonia have been identified at "
        "{locations_text}. Cases present with {symptom_list}. "
        "Concurrent influenza activity in the region is noted. "
        "An epidemiological investigation is underway.",
    ],
    "multi_outbreak": [
        "The metropolitan health department is investigating a large-scale cluster "
        "of gastrointestinal illness affecting {n_ill}+ residents across {metro_area}. "
        "Cases have been reported from multiple locations over the past {days_span} days. "
        "Symptoms vary but commonly include {symptom_list}. "
        "Both restaurant dining and grocery purchases are being investigated as potential sources."
    ]
}
```

---

## Food vehicle database structure

```json
{
  "potato_salad": {
    "display_name": "Potato salad",
    "category": "prepared_salad",
    "synonyms": ["potato salad", "potato-salad", "cold potato dish"],
    "associated_pathogens": ["s_aureus", "salmonella", "c_perfringens"],
    "typical_settings": ["potluck", "picnic", "catering"],
    "contamination_risk": "high",
    "contamination_mechanisms": [
      "prepared by hand (S. aureus handler contamination)",
      "mayonnaise-based held at room temperature",
      "cross-contamination from raw poultry"
    ],
    "typical_attack_rate_if_guilty": [0.65, 0.90]
  },
  "chicken": {
    "display_name": "Chicken (poultry)",
    "category": "poultry",
    "synonyms": ["chicken", "poultry", "fried chicken", "grilled chicken", "chicken dish"],
    "associated_pathogens": ["salmonella", "campylobacter", "c_perfringens"],
    "typical_settings": ["restaurant", "catering", "home"],
    "contamination_risk": "high",
    "contamination_mechanisms": [
      "undercooking",
      "cross-contamination during preparation",
      "improper holding temperature"
    ],
    "typical_attack_rate_if_guilty": [0.40, 0.75]
  },
  "romaine_lettuce": {
    "display_name": "Romaine lettuce",
    "category": "leafy_greens",
    "synonyms": ["romaine", "lettuce", "romaine lettuce", "salad greens", "leafy greens"],
    "associated_pathogens": ["e_coli_o157", "salmonella", "cyclospora", "norovirus"],
    "typical_settings": ["grocery_chain", "restaurant", "salad_bar"],
    "contamination_risk": "medium",
    "contamination_mechanisms": [
      "contaminated irrigation water",
      "animal intrusion in fields",
      "post-harvest handling"
    ],
    "typical_attack_rate_if_guilty": [0.25, 0.55]
  },
  "raw_oysters": {
    "display_name": "Raw oysters",
    "category": "shellfish",
    "synonyms": ["oysters", "raw oysters", "shellfish"],
    "associated_pathogens": ["vibrio_parahaemolyticus", "norovirus", "hepatitis_a"],
    "typical_settings": ["restaurant", "raw_bar", "private_event"],
    "contamination_risk": "high",
    "contamination_mechanisms": [
      "filter feeding concentrates pathogens from water",
      "harvested from contaminated waters"
    ],
    "typical_attack_rate_if_guilty": [0.35, 0.65]
  },
  "fried_rice": {
    "display_name": "Fried rice",
    "category": "grain",
    "synonyms": ["fried rice", "rice", "reheated rice"],
    "associated_pathogens": ["b_cereus_emetic"],
    "typical_settings": ["restaurant", "catering", "buffet"],
    "contamination_risk": "medium",
    "contamination_mechanisms": [
      "cooked rice held at room temperature",
      "spores survive cooking, germinate during cooling"
    ],
    "typical_attack_rate_if_guilty": [0.40, 0.70]
  },
  "ground_beef": {
    "display_name": "Ground beef",
    "category": "beef",
    "synonyms": ["ground beef", "hamburger", "beef patty", "burger"],
    "associated_pathogens": ["e_coli_o157", "salmonella"],
    "typical_settings": ["restaurant", "home", "cookout"],
    "contamination_risk": "high",
    "contamination_mechanisms": [
      "surface contamination mixed throughout during grinding",
      "undercooking"
    ],
    "typical_attack_rate_if_guilty": [0.30, 0.60]
  },
  "eggs": {
    "display_name": "Eggs",
    "category": "eggs",
    "synonyms": ["eggs", "egg dish", "scrambled eggs", "egg salad"],
    "associated_pathogens": ["salmonella_enteritidis", "s_aureus"],
    "typical_settings": ["restaurant", "bakery", "home", "catering"],
    "contamination_risk": "medium",
    "contamination_mechanisms": [
      "transovarian contamination",
      "pooling raw eggs",
      "inadequate cooking"
    ],
    "typical_attack_rate_if_guilty": [0.35, 0.65]
  },
  "raw_milk": {
    "display_name": "Raw (unpasteurized) milk",
    "category": "dairy",
    "synonyms": ["raw milk", "unpasteurized milk", "fresh milk"],
    "associated_pathogens": ["campylobacter", "salmonella", "e_coli_o157", "listeria"],
    "typical_settings": ["farm", "farmers_market", "home"],
    "contamination_risk": "very_high",
    "contamination_mechanisms": [
      "direct fecal contamination during milking",
      "no pasteurization kill step"
    ],
    "typical_attack_rate_if_guilty": [0.40, 0.70]
  },
  "deli_meat": {
    "display_name": "Deli meat",
    "category": "ready_to_eat_meat",
    "synonyms": ["deli meat", "cold cuts", "lunch meat", "sliced turkey", "sliced ham"],
    "associated_pathogens": ["listeria", "salmonella"],
    "typical_settings": ["deli", "grocery", "catering", "home"],
    "contamination_risk": "medium",
    "contamination_mechanisms": [
      "post-processing contamination",
      "Listeria growth during refrigerated storage"
    ],
    "typical_attack_rate_if_guilty": [0.15, 0.40]
  },
  "sprouts": {
    "display_name": "Sprouts (alfalfa/bean)",
    "category": "produce",
    "synonyms": ["sprouts", "alfalfa sprouts", "bean sprouts", "raw sprouts"],
    "associated_pathogens": ["salmonella", "e_coli_o157"],
    "typical_settings": ["restaurant", "grocery", "salad_bar"],
    "contamination_risk": "high",
    "contamination_mechanisms": [
      "seeds contaminated before sprouting",
      "warm, moist sprouting conditions amplify pathogens"
    ],
    "typical_attack_rate_if_guilty": [0.25, 0.55]
  }
}
```

---

## Settings database structure

```json
{
  "church_potluck": {
    "display_name": "Church potluck dinner",
    "typical_attendees": [30, 80],
    "food_service": "potluck (multiple contributors)",
    "venue_name_generator": "church_hall",
    "typical_menu": ["fried_chicken", "potato_salad", "coleslaw", "cornbread", "cake", "green_beans", "macaroni_cheese"],
    "exposure_window_hours": [2, 4],
    "investigation_difficulty": "easy"
  },
  "wedding_reception": {
    "display_name": "Wedding reception",
    "typical_attendees": [50, 200],
    "food_service": "catered",
    "venue_name_generator": "event_venue",
    "typical_menu": ["chicken_entree", "beef_entree", "salad", "rice_pilaf", "vegetables", "wedding_cake", "shrimp_cocktail"],
    "exposure_window_hours": [3, 6],
    "investigation_difficulty": "easy"
  },
  "company_picnic": {
    "display_name": "Company picnic/BBQ",
    "typical_attendees": [40, 150],
    "food_service": "catered_bbq",
    "venue_name_generator": "park",
    "typical_menu": ["hamburgers", "hot_dogs", "potato_salad", "coleslaw", "watermelon", "chips", "baked_beans"],
    "exposure_window_hours": [3, 5],
    "investigation_difficulty": "easy"
  },
  "school_cafeteria": {
    "display_name": "School cafeteria",
    "typical_attendees": [100, 500],
    "food_service": "institutional",
    "venue_name_generator": "school",
    "typical_menu": ["chicken_nuggets", "pizza", "salad_bar", "milk", "fruit", "hamburger"],
    "exposure_window_hours": [1, 2],
    "investigation_difficulty": "medium"
  },
  "restaurant_chain": {
    "display_name": "Restaurant chain (multiple locations)",
    "typical_attendees": [50, 500],
    "food_service": "restaurant",
    "venue_name_generator": "restaurant",
    "typical_menu": ["varied"],
    "exposure_window_hours": [24, 168],
    "investigation_difficulty": "hard"
  },
  "county_fair": {
    "display_name": "County fair / festival",
    "typical_attendees": [500, 5000],
    "food_service": "vendor_multiple",
    "venue_name_generator": "fairground",
    "typical_menu": ["funnel_cake", "corn_dogs", "fried_foods", "lemonade", "cotton_candy", "turkey_legs", "ice_cream"],
    "exposure_window_hours": [8, 72],
    "investigation_difficulty": "medium"
  }
}
```
