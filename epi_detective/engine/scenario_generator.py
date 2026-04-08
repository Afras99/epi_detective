"""
Scenario generator for EpiDetective.
Takes a task difficulty + random seed → produces a complete, deterministic scenario.
"""
import json
import math
import random
import os
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


PATHOGENS = load_json("pathogens.json")
FOOD_VEHICLES = load_json("food_vehicles.json")
SETTINGS = load_json("settings.json")

# Task configurations
TASK_CONFIGS = {
    "easy": {
        "name": "Point-source foodborne outbreak",
        "description": "Investigate a single-source foodborne outbreak at a shared meal event",
        "pathogen_pool": ["s_aureus", "c_perfringens", "salmonella", "norovirus", "e_coli_o157"],
        "num_attendees": [30, 80],
        "ill_fraction": [0.25, 0.50],
        "num_menu_items": [5, 7],
        "num_red_herrings": 2,
        "max_steps": 15,
        "optimal_steps": 8,
    },
    "medium": {
        "name": "Community respiratory outbreak",
        "description": "Investigate a Legionella outbreak with concurrent influenza noise",
        "pathogen_pool": ["legionella"],
        "noise_pathogen": "norovirus",
        "num_attendees": [80, 150],
        "ill_fraction": [0.15, 0.30],
        "num_menu_items": [6, 8],
        "num_red_herrings": 3,
        "max_steps": 25,
        "optimal_steps": 14,
    },
    "hard": {
        "name": "Multi-source overlapping outbreaks",
        "description": "Separate two simultaneous outbreaks in a metro area",
        "pathogen_pool_a": ["e_coli_o157", "salmonella"],
        "pathogen_pool_b": ["norovirus", "s_aureus"],
        "num_attendees": [150, 250],
        "ill_fraction": [0.20, 0.40],
        "num_menu_items": [8, 10],
        "num_red_herrings": 3,
        "max_steps": 35,
        "optimal_steps": 20,
    },
}

# First names and last names for case generation (no Faker dependency needed)
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Raymond", "Christine", "Gregory", "Debra",
    "Frank", "Rachel", "Alexander", "Carolyn", "Patrick", "Janet", "Jack", "Catherine",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales",
]


class Scenario:
    """A complete outbreak scenario with ground truth and evidence layers."""

    def __init__(self, task_id, config, setting_key, setting, pathogen_key, pathogen,
                 food_vehicle_key, food_vehicle, people, exposure_matrix, lab_results,
                 ground_truth, initial_alert, event_datetime, menu_items, red_herring_foods):
        self.task_id = task_id
        self.config = config
        self.setting_key = setting_key
        self.setting = setting
        self.pathogen_key = pathogen_key
        self.pathogen = pathogen
        self.food_vehicle_key = food_vehicle_key
        self.food_vehicle = food_vehicle
        self.people = people
        self.exposure_matrix = exposure_matrix
        self.lab_results = lab_results
        self.ground_truth = ground_truth
        self.initial_alert = initial_alert
        self.event_datetime = event_datetime
        self.menu_items = menu_items
        self.red_herring_foods = red_herring_foods
        self.max_steps = config["max_steps"]
        self.optimal_steps = config["optimal_steps"]

    @property
    def ill_people(self):
        return [p for p in self.people if p["is_ill"]]

    @property
    def well_people(self):
        return [p for p in self.people if not p["is_ill"]]


class ScenarioGenerator:

    def generate(self, task_id: str, seed: int = None) -> Scenario:
        if seed is None:
            seed = random.randint(0, 2**31)
        rng = random.Random(seed)

        config = TASK_CONFIGS[task_id]

        if task_id == "hard":
            return self._generate_hard(config, rng)

        # Pick pathogen
        pathogen_key = rng.choice(config["pathogen_pool"])
        pathogen = PATHOGENS[pathogen_key]

        # Pick food vehicle compatible with pathogen
        compatible_foods = [
            fk for fk, fv in FOOD_VEHICLES.items()
            if pathogen_key in fv["associated_pathogens"]
        ]
        if not compatible_foods:
            compatible_foods = list(FOOD_VEHICLES.keys())
        food_vehicle_key = rng.choice(compatible_foods)
        food_vehicle = FOOD_VEHICLES[food_vehicle_key]

        # Pick setting
        setting_key = rng.choice(list(SETTINGS.keys()))
        setting = SETTINGS[setting_key]

        # Generate population
        n_attendees = rng.randint(*config["num_attendees"])
        ill_frac = rng.uniform(*config["ill_fraction"])
        n_ill = max(5, int(n_attendees * ill_frac))

        # Build menu — ensure guilty food + red herrings + fillers
        menu_items = self._build_menu(food_vehicle_key, config, setting, rng)
        red_herring_foods = [m for m in menu_items if m != food_vehicle_key][:config["num_red_herrings"]]

        # Generate people
        event_datetime = datetime(2025, rng.randint(1, 12), rng.randint(1, 28), rng.randint(17, 20), 0)
        people = self._generate_people(n_attendees, n_ill, pathogen, event_datetime, rng)

        # Build exposure matrix
        exposure_matrix = self._build_exposure_matrix(
            people, food_vehicle_key, menu_items, red_herring_foods, rng
        )

        # Generate lab results
        lab_results = self._generate_lab_results(people, pathogen, pathogen_key, rng)

        # Ground truth
        ground_truth = {
            "pathogen": pathogen_key,
            "pathogen_full_name": pathogen["full_name"],
            "pathogen_synonyms": pathogen["synonyms"],
            "source": food_vehicle_key,
            "source_display_name": food_vehicle["display_name"],
            "source_synonyms": food_vehicle["synonyms"],
            "route": pathogen["transmission_routes"][0],
            "n_ill": n_ill,
            "n_attendees": n_attendees,
        }

        # Generate alert
        initial_alert = self._generate_alert(
            setting, n_ill, n_attendees, people, pathogen, event_datetime, task_id
        )

        return Scenario(
            task_id=task_id, config=config, setting_key=setting_key, setting=setting,
            pathogen_key=pathogen_key, pathogen=pathogen,
            food_vehicle_key=food_vehicle_key, food_vehicle=food_vehicle,
            people=people, exposure_matrix=exposure_matrix, lab_results=lab_results,
            ground_truth=ground_truth, initial_alert=initial_alert,
            event_datetime=event_datetime, menu_items=menu_items,
            red_herring_foods=red_herring_foods
        )

    def _generate_hard(self, config, rng):
        """Generate two overlapping outbreaks for the hard task."""
        pathogen_key_a = rng.choice(config["pathogen_pool_a"])
        pathogen_key_b = rng.choice(config["pathogen_pool_b"])
        pathogen_a = PATHOGENS[pathogen_key_a]
        pathogen_b = PATHOGENS[pathogen_key_b]

        # Pick food vehicles
        foods_a = [fk for fk, fv in FOOD_VEHICLES.items() if pathogen_key_a in fv["associated_pathogens"]]
        foods_b = [fk for fk, fv in FOOD_VEHICLES.items() if pathogen_key_b in fv["associated_pathogens"]]
        food_key_a = rng.choice(foods_a or list(FOOD_VEHICLES.keys()))
        foods_b_filtered = [f for f in (foods_b or list(FOOD_VEHICLES.keys())) if f != food_key_a]
        if not foods_b_filtered:
            foods_b_filtered = [f for f in FOOD_VEHICLES.keys() if f != food_key_a]
        food_key_b = rng.choice(foods_b_filtered)

        setting_key = rng.choice(list(SETTINGS.keys()))
        setting = SETTINGS[setting_key]

        n_attendees = rng.randint(*config["num_attendees"])
        n_ill_a = max(5, int(n_attendees * rng.uniform(0.10, 0.20)))
        n_ill_b = max(5, int(n_attendees * rng.uniform(0.10, 0.20)))
        n_ill = n_ill_a + n_ill_b

        all_menu = list(set([food_key_a, food_key_b] + rng.sample(list(FOOD_VEHICLES.keys()), min(6, len(FOOD_VEHICLES)))))
        red_herrings = [m for m in all_menu if m not in (food_key_a, food_key_b)][:3]

        event_datetime = datetime(2025, rng.randint(1, 12), rng.randint(1, 28), rng.randint(10, 18), 0)

        # Generate people — two groups
        people = []
        for i in range(n_attendees):
            is_ill_a = i < n_ill_a
            is_ill_b = (not is_ill_a) and (i < n_ill_a + n_ill_b)
            is_ill = is_ill_a or is_ill_b
            p = self._make_person(i, is_ill, event_datetime, pathogen_a if is_ill_a else pathogen_b if is_ill_b else None, rng)
            p["outbreak"] = "A" if is_ill_a else "B" if is_ill_b else "none"
            people.append(p)
        rng.shuffle(people)

        exposure_matrix = {}
        for p in people:
            exposures = {}
            for food in all_menu:
                if p["outbreak"] == "A" and food == food_key_a:
                    exposures[food] = rng.random() < rng.uniform(0.70, 0.90)
                elif p["outbreak"] == "B" and food == food_key_b:
                    exposures[food] = rng.random() < rng.uniform(0.70, 0.90)
                elif food in red_herrings:
                    exposures[food] = rng.random() < rng.uniform(0.40, 0.60)
                else:
                    exposures[food] = rng.random() < rng.uniform(0.30, 0.55)
            exposure_matrix[p["case_id"]] = exposures

        lab_results = {}
        for p in people:
            if p["is_ill"] and rng.random() < 0.65:
                ptg = pathogen_a if p["outbreak"] == "A" else pathogen_b
                ptg_key = pathogen_key_a if p["outbreak"] == "A" else pathogen_key_b
                lab_results[p["case_id"]] = {
                    "result": "POSITIVE", "organism": ptg["full_name"],
                    "pathogen_key": ptg_key
                }

        ground_truth = {
            "type": "multi_outbreak",
            "outbreak_a": {
                "pathogen": pathogen_key_a, "pathogen_synonyms": pathogen_a["synonyms"],
                "source": food_key_a, "source_synonyms": FOOD_VEHICLES[food_key_a]["synonyms"],
                "route": pathogen_a["transmission_routes"][0],
                "case_ids": [p["case_id"] for p in people if p["outbreak"] == "A"],
            },
            "outbreak_b": {
                "pathogen": pathogen_key_b, "pathogen_synonyms": pathogen_b["synonyms"],
                "source": food_key_b, "source_synonyms": FOOD_VEHICLES[food_key_b]["synonyms"],
                "route": pathogen_b["transmission_routes"][0],
                "case_ids": [p["case_id"] for p in people if p["outbreak"] == "B"],
            },
            "pathogen": pathogen_key_a,  # Primary for simple grading fallback
            "pathogen_synonyms": pathogen_a["synonyms"],
            "source": food_key_a,
            "source_synonyms": FOOD_VEHICLES[food_key_a]["synonyms"],
            "route": pathogen_a["transmission_routes"][0],
            "n_ill": n_ill, "n_attendees": n_attendees,
        }

        initial_alert = self._generate_alert(
            setting, n_ill, n_attendees, people, pathogen_a, event_datetime, "hard"
        )

        return Scenario(
            task_id="hard", config=config, setting_key=setting_key, setting=setting,
            pathogen_key=pathogen_key_a, pathogen=pathogen_a,
            food_vehicle_key=food_key_a, food_vehicle=FOOD_VEHICLES[food_key_a],
            people=people, exposure_matrix=exposure_matrix, lab_results=lab_results,
            ground_truth=ground_truth, initial_alert=initial_alert,
            event_datetime=event_datetime, menu_items=all_menu,
            red_herring_foods=red_herrings
        )

    def _build_menu(self, guilty_food, config, setting, rng):
        n_items = rng.randint(*config["num_menu_items"])
        menu = [guilty_food]
        # Add from setting's typical menu
        setting_menu = setting.get("typical_menu", [])
        for item in setting_menu:
            if item in FOOD_VEHICLES and item != guilty_food and len(menu) < n_items:
                menu.append(item)
        # Fill remaining
        all_foods = list(FOOD_VEHICLES.keys())
        rng.shuffle(all_foods)
        for item in all_foods:
            if item not in menu and len(menu) < n_items:
                menu.append(item)
        return menu[:n_items]

    def _generate_people(self, n_attendees, n_ill, pathogen, event_datetime, rng):
        people = []
        for i in range(n_attendees):
            is_ill = i < n_ill
            p = self._make_person(i, is_ill, event_datetime, pathogen if is_ill else None, rng)
            people.append(p)
        rng.shuffle(people)
        return people

    def _make_person(self, index, is_ill, event_datetime, pathogen, rng):
        age = rng.randint(5, 85)
        fname = rng.choice(FIRST_NAMES)
        lname = rng.choice(LAST_NAMES)

        onset_dt = None
        symptoms = []
        if is_ill and pathogen:
            med = pathogen["incubation_hours"]["median"]
            mu = math.log(max(med, 0.5))
            sigma = 0.35
            inc_hours = max(
                pathogen["incubation_hours"]["min"],
                min(pathogen["incubation_hours"]["max"], rng.lognormvariate(mu, sigma))
            )
            onset_dt = event_datetime + timedelta(hours=inc_hours)
            # Assign symptoms
            for symptom, prob in pathogen["symptoms"]["frequency"].items():
                if rng.random() < prob:
                    symptoms.append(symptom)
            if not symptoms:
                symptoms.append(rng.choice(pathogen["symptoms"]["primary"]))

        return {
            "case_id": f"c{index:03d}",
            "name": f"{fname} {lname}",
            "age": age,
            "sex": rng.choice(["M", "F"]),
            "is_ill": is_ill,
            "onset_datetime": onset_dt.isoformat() if onset_dt else None,
            "symptoms": symptoms,
            "hospitalized": rng.random() < 0.08 if is_ill else False,
        }

    def _build_exposure_matrix(self, people, guilty_food, menu, red_herrings, rng):
        matrix = {}
        for p in people:
            exposures = {}
            for food in menu:
                if food == guilty_food:
                    if p["is_ill"]:
                        exposures[food] = rng.random() < rng.uniform(0.75, 0.92)
                    else:
                        exposures[food] = rng.random() < rng.uniform(0.15, 0.35)
                elif food in red_herrings:
                    if p["is_ill"]:
                        exposures[food] = rng.random() < rng.uniform(0.45, 0.65)
                    else:
                        exposures[food] = rng.random() < rng.uniform(0.35, 0.55)
                else:
                    exposures[food] = rng.random() < rng.uniform(0.30, 0.60)
            matrix[p["case_id"]] = exposures
        return matrix

    def _generate_lab_results(self, people, pathogen, pathogen_key, rng):
        results = {}
        for p in people:
            if p["is_ill"] and rng.random() < 0.65:
                results[p["case_id"]] = {
                    "result": "POSITIVE",
                    "organism": pathogen["full_name"],
                    "pathogen_key": pathogen_key,
                    "test_method": pathogen["lab_confirmation"].split()[0],
                }
            elif p["is_ill"]:
                results[p["case_id"]] = {
                    "result": "PENDING",
                    "organism": None,
                    "note": "Specimen collected, awaiting results"
                }
        return results

    def _generate_alert(self, setting, n_ill, n_attendees, people, pathogen, event_dt, task_id):
        ill_people = [p for p in people if p["is_ill"]]
        symptoms = {}
        for p in ill_people:
            for s in p.get("symptoms", []):
                symptoms[s] = symptoms.get(s, 0) + 1
        top_symptoms = sorted(symptoms.keys(), key=lambda x: symptoms[x], reverse=True)[:4]
        symptom_str = ", ".join(s.replace("_", " ") for s in top_symptoms)

        hosp_count = sum(1 for p in ill_people if p.get("hospitalized"))
        hosp_text = f"{hosp_count} individuals have been hospitalized." if hosp_count > 0 else "No hospitalizations reported."

        date_str = event_dt.strftime("%A, %B %d, %Y")

        if task_id == "easy":
            return (
                f"The county health department received reports of {n_ill} people experiencing "
                f"gastrointestinal illness following a {setting['display_name'].lower()} held on "
                f"{date_str}. Approximately {n_attendees} people attended. "
                f"Symptoms reported include {symptom_str}. "
                f"{hosp_text} An epidemiological investigation has been initiated. "
                f"Your task: identify the causative pathogen, the contaminated food source, "
                f"and the transmission route."
            )
        elif task_id == "medium":
            return (
                f"The state health department has been notified of an unusual cluster of "
                f"respiratory and gastrointestinal illness across multiple facilities. Over the "
                f"past week, {n_ill} cases have been identified. Cases present with {symptom_str}. "
                f"Concurrent seasonal influenza activity is noted in the region. "
                f"{hosp_text} An investigation is underway to determine whether these cases "
                f"represent a single outbreak or multiple unrelated illness clusters. "
                f"Your task: identify the causative pathogen, the source of exposure, "
                f"and the transmission route."
            )
        else:
            return (
                f"The metropolitan health department is investigating a large cluster of "
                f"gastrointestinal illness affecting {n_ill}+ residents. Cases have been reported "
                f"from multiple locations over the past week. Symptoms vary but commonly include "
                f"{symptom_str}. Initial analysis suggests the cases may not all share a single "
                f"source. {hosp_text} "
                f"Your task: determine if this is one outbreak or multiple, identify pathogen(s), "
                f"source(s), and transmission route(s)."
            )
