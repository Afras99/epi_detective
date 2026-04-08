# EpiDetective — Full Implementation Plan

## 1. Architecture Overview

```
epidetective/
├── server/
│   ├── app.py                  # FastAPI + OpenEnv create_fastapi_app
│   ├── environment.py          # EpiDetectiveEnv(Environment)
│   ├── models.py               # Action, Observation, State (Pydantic)
│   ├── scenario_engine.py      # Generates outbreak scenarios from templates
│   ├── grader.py               # Deterministic component-wise scoring
│   ├── data/
│   │   ├── pathogens.json      # Pathogen knowledge base
│   │   ├── food_vehicles.json  # Food-pathogen associations
│   │   ├── settings.json       # Outbreak settings (restaurant, school, etc.)
│   │   ├── names.json          # Synthetic name pools
│   │   ├── symptoms.json       # Symptom profiles per pathogen
│   │   └── scenarios/          # Pre-built scenario templates (10-15)
│   │       ├── easy_01.json
│   │       ├── easy_02.json
│   │       ├── medium_01.json
│   │       ├── medium_02.json
│   │       ├── hard_01.json
│   │       └── ...
│   ├── requirements.txt
│   └── Dockerfile
├── client/
│   ├── __init__.py
│   ├── client.py               # EpiDetectiveClient(HTTPEnvClient)
│   └── models.py               # Shared Pydantic models
├── inference.py                # LLM agent script (OpenAI Client)
├── pyproject.toml
└── README.md
```

---

## 2. Data Sources — The Core of Realism

### 2.1 Pathogen Knowledge Base (`pathogens.json`)

**Source: FDA "Foodborne Illness-Causing Organisms" table + CDC/NIH literature**

This is the single most important data file. Every scenario is generated from this base.

```json
{
  "pathogens": [
    {
      "id": "salmonella",
      "name": "Salmonella spp.",
      "common_name": "Salmonellosis",
      "type": "bacteria",
      "gram": "negative",
      "transmission": ["foodborne", "animal_contact", "person_to_person"],
      "incubation": {
        "min_hours": 6,
        "median_hours": 24,
        "max_hours": 72
      },
      "duration": {
        "min_days": 4,
        "max_days": 7
      },
      "symptoms": {
        "primary": ["diarrhea", "fever", "abdominal_cramps", "vomiting"],
        "secondary": ["headache", "myalgia"],
        "distinguishing": ["fever_prominent"]
      },
      "severity": {
        "hospitalization_rate": 0.29,
        "case_fatality_rate": 0.005
      },
      "food_vehicles": [
        {"food": "eggs", "weight": 0.25},
        {"food": "poultry", "weight": 0.25},
        {"food": "meat", "weight": 0.15},
        {"food": "unpasteurized_milk", "weight": 0.10},
        {"food": "raw_fruits_vegetables", "weight": 0.10},
        {"food": "cheese", "weight": 0.05},
        {"food": "juice_unpasteurized", "weight": 0.05},
        {"food": "sprouts", "weight": 0.05}
      ],
      "contributing_factors": [
        "inadequate_cooking",
        "cross_contamination",
        "infected_food_handler",
        "improper_holding_temperature"
      ],
      "lab_tests": ["stool_culture", "blood_culture", "PFGE", "WGS"],
      "environmental_sources": ["poultry_farm", "egg_processing", "restaurant_kitchen"],
      "attack_rate_range": [0.20, 0.60],
      "serotypes": ["Enteritidis", "Typhimurium", "Newport", "Heidelberg", "Javiana"]
    },
    {
      "id": "norovirus",
      "name": "Norovirus",
      "common_name": "Viral gastroenteritis",
      "type": "virus",
      "transmission": ["foodborne", "person_to_person", "environmental"],
      "incubation": {
        "min_hours": 12,
        "median_hours": 33,
        "max_hours": 48
      },
      "duration": {
        "min_days": 1,
        "max_days": 3
      },
      "symptoms": {
        "primary": ["vomiting", "diarrhea", "abdominal_cramps", "nausea"],
        "secondary": ["headache", "low_grade_fever", "myalgia"],
        "distinguishing": ["projectile_vomiting", "rapid_onset_vomiting"]
      },
      "severity": {
        "hospitalization_rate": 0.04,
        "case_fatality_rate": 0.001
      },
      "food_vehicles": [
        {"food": "leafy_greens", "weight": 0.20},
        {"food": "fresh_fruits", "weight": 0.15},
        {"food": "shellfish_raw", "weight": 0.20},
        {"food": "ready_to_eat_foods", "weight": 0.25},
        {"food": "contaminated_water", "weight": 0.10}
      ],
      "contributing_factors": [
        "infected_food_handler",
        "bare_hand_contact",
        "inadequate_handwashing",
        "contaminated_water_source"
      ],
      "lab_tests": ["RT-PCR_stool", "electron_microscopy"],
      "environmental_sources": ["food_handler_illness", "contaminated_water"],
      "attack_rate_range": [0.30, 0.70]
    },
    {
      "id": "ecoli_o157",
      "name": "E. coli O157:H7",
      "common_name": "Hemorrhagic colitis",
      "type": "bacteria",
      "gram": "negative",
      "transmission": ["foodborne", "waterborne", "person_to_person"],
      "incubation": {
        "min_hours": 24,
        "median_hours": 72,
        "max_hours": 192
      },
      "duration": {
        "min_days": 5,
        "max_days": 10
      },
      "symptoms": {
        "primary": ["bloody_diarrhea", "severe_abdominal_pain", "vomiting"],
        "secondary": ["low_grade_fever_or_none"],
        "distinguishing": ["bloody_diarrhea", "absence_of_high_fever"]
      },
      "severity": {
        "hospitalization_rate": 0.45,
        "case_fatality_rate": 0.01,
        "hus_rate": 0.06
      },
      "food_vehicles": [
        {"food": "ground_beef", "weight": 0.30},
        {"food": "leafy_greens", "weight": 0.20},
        {"food": "unpasteurized_milk", "weight": 0.10},
        {"food": "sprouts", "weight": 0.10},
        {"food": "raw_flour", "weight": 0.05},
        {"food": "contaminated_water", "weight": 0.10}
      ],
      "contributing_factors": [
        "undercooked_ground_beef",
        "cross_contamination",
        "contaminated_produce",
        "unpasteurized_products"
      ],
      "lab_tests": ["stool_culture_SMAC", "shiga_toxin_EIA", "PFGE", "WGS"],
      "environmental_sources": ["cattle_farm", "processing_plant", "irrigation_water"],
      "attack_rate_range": [0.15, 0.45]
    },
    {
      "id": "staph_aureus",
      "name": "Staphylococcus aureus",
      "common_name": "Staphylococcal food poisoning",
      "type": "bacteria_toxin",
      "gram": "positive",
      "transmission": ["foodborne"],
      "incubation": {
        "min_hours": 1,
        "median_hours": 3,
        "max_hours": 6
      },
      "duration": {
        "min_days": 1,
        "max_days": 2
      },
      "symptoms": {
        "primary": ["severe_nausea", "vomiting", "abdominal_cramps"],
        "secondary": ["diarrhea", "low_grade_fever"],
        "distinguishing": ["sudden_onset", "predominant_vomiting", "very_short_incubation"]
      },
      "severity": {
        "hospitalization_rate": 0.06,
        "case_fatality_rate": 0.0001
      },
      "food_vehicles": [
        {"food": "potato_salad", "weight": 0.20},
        {"food": "egg_salad", "weight": 0.15},
        {"food": "cream_pastries", "weight": 0.15},
        {"food": "sliced_deli_meat", "weight": 0.15},
        {"food": "sandwiches", "weight": 0.15},
        {"food": "dairy_products", "weight": 0.10}
      ],
      "contributing_factors": [
        "improper_holding_temperature",
        "infected_food_handler_skin_wound",
        "prolonged_room_temperature_storage"
      ],
      "lab_tests": ["stool_enterotoxin_detection", "food_sample_culture", "phage_typing"],
      "environmental_sources": ["food_handler_wound", "nasal_carriage"],
      "attack_rate_range": [0.40, 0.80]
    },
    {
      "id": "listeria",
      "name": "Listeria monocytogenes",
      "common_name": "Listeriosis",
      "type": "bacteria",
      "gram": "positive",
      "transmission": ["foodborne"],
      "incubation": {
        "min_hours": 48,
        "median_hours": 504,
        "max_hours": 1008
      },
      "duration": {
        "min_days": 7,
        "max_days": 21
      },
      "symptoms": {
        "primary": ["fever", "muscle_aches", "nausea", "diarrhea"],
        "secondary": ["headache", "stiff_neck", "confusion", "loss_of_balance"],
        "distinguishing": ["long_incubation", "meningitis_risk", "pregnancy_complications"]
      },
      "severity": {
        "hospitalization_rate": 0.94,
        "case_fatality_rate": 0.20
      },
      "food_vehicles": [
        {"food": "deli_meats", "weight": 0.25},
        {"food": "soft_cheeses", "weight": 0.25},
        {"food": "unpasteurized_milk", "weight": 0.15},
        {"food": "smoked_seafood", "weight": 0.15},
        {"food": "raw_sprouts", "weight": 0.10},
        {"food": "melon_cantaloupe", "weight": 0.10}
      ],
      "contributing_factors": [
        "post_processing_contamination",
        "inadequate_refrigeration",
        "cross_contamination_deli_slicer",
        "biofilm_formation"
      ],
      "lab_tests": ["blood_culture", "CSF_culture", "PFGE", "WGS"],
      "environmental_sources": ["deli_equipment", "processing_plant_drains", "cold_storage"],
      "attack_rate_range": [0.01, 0.10]
    },
    {
      "id": "clostridium_perfringens",
      "name": "Clostridium perfringens",
      "common_name": "Perfringens food poisoning",
      "type": "bacteria_toxin",
      "gram": "positive",
      "transmission": ["foodborne"],
      "incubation": {
        "min_hours": 8,
        "median_hours": 12,
        "max_hours": 16
      },
      "duration": {
        "min_days": 1,
        "max_days": 1
      },
      "symptoms": {
        "primary": ["intense_abdominal_cramps", "watery_diarrhea"],
        "secondary": [],
        "distinguishing": ["no_vomiting", "no_fever", "cramps_dominant"]
      },
      "severity": {
        "hospitalization_rate": 0.02,
        "case_fatality_rate": 0.0005
      },
      "food_vehicles": [
        {"food": "meat_stews", "weight": 0.25},
        {"food": "gravy", "weight": 0.20},
        {"food": "poultry", "weight": 0.20},
        {"food": "casseroles", "weight": 0.15},
        {"food": "beans", "weight": 0.10}
      ],
      "contributing_factors": [
        "improper_cooling",
        "inadequate_reheating",
        "bulk_food_preparation",
        "prolonged_holding_warm_temperature"
      ],
      "lab_tests": ["stool_spore_count", "food_sample_spore_count", "enterotoxin_detection"],
      "environmental_sources": ["catering_kitchen", "institutional_kitchen"],
      "attack_rate_range": [0.30, 0.70]
    },
    {
      "id": "campylobacter",
      "name": "Campylobacter jejuni",
      "common_name": "Campylobacteriosis",
      "type": "bacteria",
      "gram": "negative",
      "transmission": ["foodborne", "waterborne", "animal_contact"],
      "incubation": {
        "min_hours": 48,
        "median_hours": 72,
        "max_hours": 120
      },
      "duration": {
        "min_days": 2,
        "max_days": 10
      },
      "symptoms": {
        "primary": ["diarrhea", "cramps", "fever", "vomiting"],
        "secondary": ["bloody_diarrhea", "headache"],
        "distinguishing": ["bloody_diarrhea_possible", "moderate_fever"]
      },
      "severity": {
        "hospitalization_rate": 0.15,
        "case_fatality_rate": 0.001
      },
      "food_vehicles": [
        {"food": "raw_undercooked_poultry", "weight": 0.40},
        {"food": "unpasteurized_milk", "weight": 0.20},
        {"food": "contaminated_water", "weight": 0.20},
        {"food": "raw_produce", "weight": 0.10}
      ],
      "contributing_factors": [
        "undercooked_poultry",
        "cross_contamination",
        "unpasteurized_products",
        "contaminated_water"
      ],
      "lab_tests": ["stool_culture_selective_media", "PCR"],
      "environmental_sources": ["poultry_processing", "raw_milk_dairy", "surface_water"],
      "attack_rate_range": [0.15, 0.40]
    },
    {
      "id": "vibrio_parahaemolyticus",
      "name": "Vibrio parahaemolyticus",
      "common_name": "V. parahaemolyticus infection",
      "type": "bacteria",
      "gram": "negative",
      "transmission": ["foodborne"],
      "incubation": {
        "min_hours": 4,
        "median_hours": 17,
        "max_hours": 96
      },
      "duration": {
        "min_days": 2,
        "max_days": 5
      },
      "symptoms": {
        "primary": ["watery_diarrhea", "abdominal_cramps", "nausea", "vomiting", "fever"],
        "secondary": ["bloody_diarrhea_occasional"],
        "distinguishing": ["seafood_association", "coastal_summer"]
      },
      "food_vehicles": [
        {"food": "raw_oysters", "weight": 0.35},
        {"food": "raw_shellfish", "weight": 0.30},
        {"food": "undercooked_seafood", "weight": 0.25},
        {"food": "sushi_sashimi", "weight": 0.10}
      ],
      "contributing_factors": [
        "inadequate_refrigeration_seafood",
        "raw_consumption",
        "warm_water_harvest"
      ],
      "lab_tests": ["stool_culture_TCBS", "PCR_tdh_trh"],
      "environmental_sources": ["coastal_waters", "oyster_beds", "seafood_market"],
      "attack_rate_range": [0.20, 0.50]
    },
    {
      "id": "shigella",
      "name": "Shigella spp.",
      "common_name": "Shigellosis (Bacillary dysentery)",
      "type": "bacteria",
      "gram": "negative",
      "transmission": ["foodborne", "person_to_person", "waterborne"],
      "incubation": {
        "min_hours": 24,
        "median_hours": 36,
        "max_hours": 48
      },
      "duration": {
        "min_days": 4,
        "max_days": 7
      },
      "symptoms": {
        "primary": ["abdominal_cramps", "fever", "diarrhea"],
        "secondary": ["bloody_mucoid_stools"],
        "distinguishing": ["mucoid_bloody_stools", "tenesmus", "high_fever"]
      },
      "severity": {
        "hospitalization_rate": 0.20,
        "case_fatality_rate": 0.002
      },
      "food_vehicles": [
        {"food": "raw_produce", "weight": 0.30},
        {"food": "contaminated_water", "weight": 0.25},
        {"food": "ready_to_eat_foods", "weight": 0.25}
      ],
      "contributing_factors": [
        "infected_food_handler",
        "inadequate_handwashing",
        "contaminated_water",
        "person_to_person_spread"
      ],
      "lab_tests": ["stool_culture", "PCR", "serotyping"],
      "environmental_sources": ["daycare_center", "food_handler", "contaminated_water_supply"],
      "attack_rate_range": [0.25, 0.55]
    },
    {
      "id": "legionella",
      "name": "Legionella pneumophila",
      "common_name": "Legionnaires' disease",
      "type": "bacteria",
      "gram": "negative",
      "transmission": ["environmental_aerosol"],
      "incubation": {
        "min_hours": 48,
        "median_hours": 144,
        "max_hours": 240
      },
      "duration": {
        "min_days": 7,
        "max_days": 21
      },
      "symptoms": {
        "primary": ["high_fever", "cough", "shortness_of_breath", "muscle_aches"],
        "secondary": ["headache", "diarrhea", "confusion"],
        "distinguishing": ["pneumonia", "not_foodborne", "aerosol_transmission"]
      },
      "severity": {
        "hospitalization_rate": 0.85,
        "case_fatality_rate": 0.10
      },
      "food_vehicles": [],
      "contributing_factors": [
        "contaminated_cooling_tower",
        "contaminated_hot_water_system",
        "decorative_fountain",
        "hot_tub_spa"
      ],
      "lab_tests": ["urine_antigen_test", "sputum_culture", "PCR_respiratory"],
      "environmental_sources": ["cooling_tower", "hot_water_system", "decorative_fountain"],
      "attack_rate_range": [0.01, 0.05]
    }
  ]
}
```

### Where this data comes from (citations for README):
- **FDA**: "Foodborne Illness-Causing Organisms in the U.S." reference table (fda.gov/media/77727)
- **CDC NORS/FDOSS**: National Outbreak Reporting System — outbreak settings, contributing factors, food categorization (via IFSAC scheme)
- **CDC MMWR SS-6710**: Surveillance for Foodborne Disease Outbreaks 2009–2015 — pathogen-food pair frequencies, outbreak sizes, setting distributions
- **CDC MMWR SS-7401**: Contributing Factors of Foodborne Illness Outbreaks 2014–2022 — contamination/proliferation/survival factor distributions
- **PMC6805792**: "Incubation periods of enteric illnesses in foodborne outbreaks, US 1998–2013" — median and range of outbreak incubation periods per pathogen
- **PMC6604998**: "Foodborne pathogens" review — comprehensive pathogen characteristics
- **NCBI Pathogen Detection**: Genomic surveillance data structure for WGS-based investigation scenarios

### 2.2 Food Vehicle Database (`food_vehicles.json`)

**Source: CDC IFSAC food categorization + NORS outbreak data**

```json
{
  "food_categories": {
    "eggs": {
      "settings": ["restaurant", "catering", "home"],
      "preparation_methods": ["scrambled", "sunny_side_up", "in_baked_goods", "egg_salad"],
      "contamination_points": ["farm", "processing", "preparation"],
      "common_pathogens": ["salmonella"]
    },
    "poultry": {
      "settings": ["restaurant", "catering", "home", "grocery"],
      "preparation_methods": ["roasted", "fried", "grilled", "deli_sliced"],
      "contamination_points": ["farm", "processing", "preparation", "cross_contamination"],
      "common_pathogens": ["salmonella", "campylobacter"]
    },
    "ground_beef": {
      "settings": ["restaurant", "fast_food", "home", "school_cafeteria"],
      "preparation_methods": ["hamburger", "meatloaf", "taco_meat", "meatballs"],
      "contamination_points": ["slaughterhouse", "grinding", "undercooked"],
      "common_pathogens": ["ecoli_o157"]
    },
    "leafy_greens": {
      "settings": ["restaurant", "home", "salad_bar", "grocery"],
      "preparation_methods": ["raw_salad", "garnish", "sandwich"],
      "contamination_points": ["irrigation_water", "field", "processing_wash"],
      "common_pathogens": ["ecoli_o157", "norovirus", "cyclospora"]
    },
    "shellfish_raw": {
      "settings": ["restaurant", "oyster_bar", "catering"],
      "preparation_methods": ["raw_on_half_shell", "ceviche", "sushi"],
      "contamination_points": ["harvest_water", "improper_refrigeration"],
      "common_pathogens": ["vibrio_parahaemolyticus", "norovirus"]
    },
    "deli_meats": {
      "settings": ["restaurant", "deli", "grocery", "home"],
      "preparation_methods": ["sliced_cold", "sandwich", "party_platter"],
      "contamination_points": ["deli_slicer", "post_processing", "improper_storage"],
      "common_pathogens": ["listeria"]
    },
    "potato_salad": {
      "settings": ["picnic", "catering", "potluck", "wedding_reception"],
      "preparation_methods": ["cold_side_dish"],
      "contamination_points": ["food_handler", "prolonged_room_temp"],
      "common_pathogens": ["staph_aureus"]
    },
    "rice_cooked": {
      "settings": ["restaurant", "catering", "buffet"],
      "preparation_methods": ["fried_rice", "steamed_held_warm"],
      "contamination_points": ["improper_cooling", "holding_temperature"],
      "common_pathogens": ["bacillus_cereus"]
    }
  }
}
```

### 2.3 Outbreak Settings Database (`settings.json`)

**Source: NORS setting categories + MMWR outbreak surveillance reports**

```json
{
  "settings": {
    "wedding_reception": {
      "typical_attendees": [50, 200],
      "food_service": "catering",
      "exposure_window_hours": 4,
      "typical_menu": ["chicken", "potato_salad", "cake", "salad", "rice"],
      "risk_factors": ["buffet_service", "outdoor_temp", "large_batch_prep"]
    },
    "restaurant": {
      "typical_attendees": [10, 100],
      "food_service": "commercial_kitchen",
      "exposure_window_hours": 2,
      "typical_menu": ["varied"],
      "risk_factors": ["food_handler_hygiene", "cross_contamination", "temp_control"]
    },
    "school_cafeteria": {
      "typical_attendees": [100, 500],
      "food_service": "institutional",
      "exposure_window_hours": 1,
      "typical_menu": ["hamburgers", "chicken_nuggets", "milk", "salad_bar"],
      "risk_factors": ["bulk_preparation", "holding_temp", "young_population"]
    },
    "county_fair": {
      "typical_attendees": [200, 5000],
      "food_service": "multiple_vendors",
      "exposure_window_hours": 12,
      "typical_menu": ["varied_vendor"],
      "risk_factors": ["outdoor_temp", "multiple_vendors", "handwashing_access"]
    },
    "nursing_home": {
      "typical_attendees": [50, 200],
      "food_service": "institutional",
      "exposure_window_hours": 24,
      "typical_menu": ["soft_foods", "deli_meats", "dairy"],
      "risk_factors": ["vulnerable_population", "person_to_person", "institutional_kitchen"]
    },
    "cruise_ship": {
      "typical_attendees": [500, 3000],
      "food_service": "buffet_dining",
      "exposure_window_hours": 168,
      "typical_menu": ["buffet_varied"],
      "risk_factors": ["closed_environment", "person_to_person", "multiple_exposures"]
    },
    "daycare_center": {
      "typical_attendees": [20, 80],
      "food_service": "provided_meals",
      "exposure_window_hours": 8,
      "typical_menu": ["simple_meals", "snacks", "milk"],
      "risk_factors": ["diaper_changing", "person_to_person", "hand_hygiene"]
    }
  }
}
```

### 2.4 Synthetic Person Generator (`names.json` + generation logic)

**Source: US Census Bureau popular names + Faker library for demographics**

```python
# Scenario engine uses these to generate realistic line lists
DEMOGRAPHICS = {
    "age_distributions": {
        "wedding_reception": {"mean": 38, "std": 15, "min": 5, "max": 85},
        "school_cafeteria": {"mean": 12, "std": 3, "min": 6, "max": 18},
        "nursing_home": {"mean": 78, "std": 8, "min": 65, "max": 98},
        "daycare_center": {"mean": 3, "std": 1.5, "min": 1, "max": 6},
        "county_fair": {"mean": 35, "std": 18, "min": 3, "max": 80},
    },
    "sex_ratio": 0.5,  # M/F
}
```

### 2.5 Symptoms Database (`symptoms.json`)

**Source: FDA reference table + clinical literature**

```json
{
  "symptom_profiles": {
    "salmonella": {
      "symptom_rates": {
        "diarrhea": 0.90,
        "fever": 0.70,
        "abdominal_cramps": 0.85,
        "vomiting": 0.45,
        "nausea": 0.60,
        "headache": 0.35,
        "bloody_stool": 0.10,
        "myalgia": 0.30
      }
    },
    "norovirus": {
      "symptom_rates": {
        "vomiting": 0.85,
        "diarrhea": 0.75,
        "nausea": 0.90,
        "abdominal_cramps": 0.70,
        "low_grade_fever": 0.30,
        "headache": 0.40,
        "myalgia": 0.25,
        "chills": 0.20
      }
    },
    "ecoli_o157": {
      "symptom_rates": {
        "bloody_diarrhea": 0.70,
        "severe_abdominal_pain": 0.90,
        "vomiting": 0.35,
        "low_grade_fever": 0.15,
        "watery_diarrhea_initial": 0.80
      }
    },
    "staph_aureus": {
      "symptom_rates": {
        "severe_nausea": 0.95,
        "vomiting": 0.90,
        "abdominal_cramps": 0.80,
        "diarrhea": 0.50,
        "fever": 0.10
      }
    }
  }
}
```

---

## 3. Scenario Generation Engine

The engine creates reproducible outbreak scenarios from templates + randomization:

```python
class ScenarioEngine:
    """
    Generates outbreak scenarios using:
    1. Real epidemiological parameters from pathogen KB
    2. Real outbreak patterns from NORS/MMWR data
    3. Synthetic but realistic case data
    
    Each scenario has a PLANTED GROUND TRUTH that enables
    deterministic grading.
    """
    
    def generate_scenario(self, difficulty: str, seed: int) -> Scenario:
        rng = random.Random(seed)
        
        if difficulty == "easy":
            # Single pathogen, single food source, clear epi curve
            # 30-80 attendees, 10-25 ill
            # 2-3 red herring exposures with low attack rates
            # Classic point-source epi curve shape
            return self._generate_point_source(rng)
            
        elif difficulty == "medium":
            # Single pathogen, but with confounders
            # 80-200 people, spread across multiple settings
            # Environmental source (not foodborne) for Legionella variant
            # Background noise from concurrent illness season
            # 4-5 red herring exposures
            return self._generate_community_outbreak(rng)
            
        elif difficulty == "hard":
            # TWO overlapping outbreaks (different pathogens, different sources)
            # 150-300 people across a metro area
            # Temporal and geographic overlap makes them look like one outbreak
            # Agent must correctly separate into 2 distinct outbreaks
            return self._generate_multi_source(rng)
    
    def _generate_point_source(self, rng) -> Scenario:
        """
        Template: Wedding/event/fair with catered food.
        1. Pick pathogen (weighted by outbreak frequency)
        2. Pick food vehicle (from pathogen's food_vehicles)
        3. Pick setting
        4. Generate attendee list with demographics
        5. Assign illness based on:
           - Did they eat the implicated food? (attack rate from KB)
           - Did they eat non-implicated food? (background rate 2-5%)
        6. Generate onset times from incubation distribution
        7. Assign symptoms from symptom_rates (with individual variation)
        8. Add 2-3 red herring foods with 5-15% illness rate (noise)
        """
        # Select pathogen
        pathogen = rng.choices(
            ["salmonella", "staph_aureus", "clostridium_perfringens", "norovirus"],
            weights=[0.35, 0.25, 0.20, 0.20]
        )[0]
        
        pathogen_data = self.pathogens[pathogen]
        
        # Select food vehicle
        food = rng.choices(
            [f["food"] for f in pathogen_data["food_vehicles"]],
            weights=[f["weight"] for f in pathogen_data["food_vehicles"]]
        )[0]
        
        # Generate cases...
        # (full implementation generates complete line lists, 
        #  exposure histories, onset times, symptoms per case)
        
        return Scenario(
            ground_truth=GroundTruth(
                pathogen=pathogen,
                food_vehicle=food,
                transmission_route="foodborne",
                contributing_factors=[...],
                source_setting=setting
            ),
            # ... all generated data
        )
```

---

## 4. Environment API Design

### 4.1 Pydantic Models (`models.py`)

```python
from pydantic import BaseModel
from typing import Optional, Literal
from enum import Enum

class ActionType(str, Enum):
    VIEW_ALERT = "view_alert"
    REQUEST_LINE_LIST = "request_line_list"
    VIEW_EPI_CURVE = "view_epi_curve"
    REQUEST_LAB_RESULTS = "request_lab_results"
    GET_EXPOSURE_HISTORY = "get_exposure_history"
    CALCULATE_ATTACK_RATE = "calculate_attack_rate"
    CALCULATE_ODDS_RATIO = "calculate_odds_ratio"
    REQUEST_ENVIRONMENTAL_SAMPLES = "request_environmental_samples"
    REVIEW_FOOD_PREP_RECORDS = "review_food_prep_records"
    INTERVIEW_FOOD_HANDLER = "interview_food_handler"
    SUBMIT_HYPOTHESIS = "submit_hypothesis"
    SUBMIT_FINAL_ANSWER = "submit_final_answer"

class EpiDetectiveAction(BaseModel):
    action_type: ActionType
    parameters: dict = {}  
    # e.g., {"case_ids": [1,2,3]} for lab results
    # e.g., {"food_item": "potato_salad"} for attack rate
    # e.g., {"location": "kitchen_A"} for env samples

class EpiDetectiveObservation(BaseModel):
    task_id: str
    difficulty: str
    step_number: int
    max_steps: int
    data: dict          # The actual response data
    narrative: str      # Natural language description
    available_actions: list[str]
    reward: float
    done: bool
    score: Optional[float] = None  # Only populated on final answer

class EpiDetectiveState(BaseModel):
    episode_id: str
    task_id: str
    difficulty: str
    step_count: int
    max_steps: int
    actions_taken: list[str]
    data_unlocked: list[str]  # What data the agent has accessed
    hypotheses_submitted: list[dict]
    done: bool
    final_score: Optional[float] = None
```

### 4.2 Step Limits Per Difficulty

| Difficulty | Max Steps | Optimal Steps | Efficiency Bonus Threshold |
|---|---|---|---|
| Easy | 20 | 6-8 | ≤10 steps |
| Medium | 30 | 10-15 | ≤18 steps |
| Hard | 40 | 15-25 | ≤28 steps |

---

## 5. Grading System (Fully Deterministic)

### Task 1 (Easy) — Point-Source Foodborne Outbreak
```
Score = (
    0.25 × pathogen_match          # Exact match from synonym set
  + 0.25 × food_vehicle_match      # Exact match from alias set
  + 0.20 × transmission_route_match # Categorical: foodborne/waterborne/airborne/person-to-person
  + 0.15 × case_definition_quality  # Checklist: includes person/place/time criteria
  + 0.15 × efficiency_bonus         # (1 - steps_used/max_steps), clamped [0,1]
)
```

### Task 2 (Medium) — Community Outbreak with Confounders
```
Score = (
    0.20 × pathogen_match
  + 0.20 × source_match            # Environmental source identification
  + 0.15 × transmission_route_match
  + 0.15 × confounder_handling     # Did agent correctly distinguish from background illness?
  + 0.15 × case_definition_quality
  + 0.15 × efficiency_bonus
)
```

### Task 3 (Hard) — Multi-Source, Multi-Pathogen
```
Score = (
    0.30 × outbreak_separation_f1  # Precision × Recall over case-to-outbreak assignment
  + 0.15 × pathogen_1_match
  + 0.15 × pathogen_2_match
  + 0.10 × source_1_match
  + 0.10 × source_2_match
  + 0.10 × route_match_both
  + 0.10 × efficiency_bonus
)
```

### Intermediate Reward (Dense Signal)
```python
def calculate_step_reward(self, action, result):
    """
    Dense reward at every step:
    - +0.02 for first time accessing a new data type (encourages exploration)
    - +0.01-0.05 for high-information-gain queries (calculated via ground truth)
    - +0.00 for redundant queries
    - -0.01 for clearly irrelevant actions
    - submit_hypothesis: partial score (0.0-0.3) based on component matches
    """
```

---

## 6. Day-by-Day Build Plan

### Day 1: Data Layer + Scaffold (6-8 hrs)
- [ ] `openenv init epidetective` — scaffold project
- [ ] Build `pathogens.json` (all 10 pathogens, copy from above + fill gaps)
- [ ] Build `food_vehicles.json`, `settings.json`, `symptoms.json`
- [ ] Write `scenario_engine.py` — the core generator
- [ ] Unit test: generate 20 scenarios, verify all have valid ground truth

### Day 2: Environment Core (6-8 hrs)
- [ ] Implement `models.py` — all Pydantic models
- [ ] Implement `environment.py` — `reset()`, `step()`, `state()`
- [ ] Implement all 12 action handlers (view_alert, request_line_list, etc.)
- [ ] Wire up the data-gating: each action unlocks specific data
- [ ] Unit test: run through a complete easy scenario manually

### Day 3: Grading + Reward (5-6 hrs)
- [ ] Implement `grader.py` — all three task graders
- [ ] Implement intermediate reward function
- [ ] Build synonym/alias sets for pathogen matching (e.g., "Salmonella" = "salmonella spp." = "S. enterica")
- [ ] Build food alias sets (e.g., "potato salad" = "potato_salad" = "cold potato dish")
- [ ] Unit test: verify grading produces expected scores for known inputs

### Day 4: Scenario Templates + Polish (5-6 hrs)
- [ ] Create 3 easy scenario templates (wedding/Salmonella, fair/Staph, school/Norovirus)
- [ ] Create 2 medium templates (Legionella/cooling tower, multi-setting E. coli)
- [ ] Create 2 hard templates (overlapping Salmonella + Norovirus, E. coli + Listeria)
- [ ] Add parametric randomization so each template can produce 10+ variants
- [ ] Test difficulty curve: easy should be ~70-80% solvable, hard should be ~20-30%

### Day 5: LLM Agent + Docker (5-6 hrs)
- [ ] Write `inference.py` — the LLM agent using OpenAI Client
- [ ] System prompt engineering: teach the LLM the investigation workflow
- [ ] Implement the agent loop: observe → reason → act → observe
- [ ] Write Dockerfile (FROM openenv-base)
- [ ] Test locally with Docker

### Day 6: HF Deployment + Web UI (4-5 hrs)
- [ ] Deploy to Hugging Face Spaces
- [ ] Enable Gradio web interface (`create_web_interface_app`)
- [ ] Verify all three tasks work end-to-end via the deployed URL
- [ ] `openenv validate` — pass all automated checks
- [ ] Test: inference completes under 20 minutes on 2 vCPU / 8GB

### Day 7: README + Edge Cases + Buffer (4-5 hrs)
- [ ] Write comprehensive README with:
  - Real-world motivation
  - Data sources and citations
  - Architecture diagram
  - Sample episode transcript
  - Performance benchmarks
- [ ] Fix any edge cases found during testing
- [ ] Final submission

---

## 7. Key Implementation Details

### Epi Curve Generation
```python
def generate_epi_curve(self, cases, grouping="6_hour"):
    """
    Generates realistic epidemic curves from onset times.
    Point-source: log-normal distribution
    Propagated: multiple waves
    """
    onset_times = [c.onset_datetime for c in cases if c.is_ill]
    # Bin by grouping interval
    bins = self._create_time_bins(onset_times, grouping)
    return {
        "type": "histogram",
        "bins": bins,
        "x_label": "Date/Time of Illness Onset",
        "y_label": "Number of Cases",
        "interpretation_hint": self._classify_curve_shape(bins)
    }
```

### Attack Rate Calculation
```python
def calculate_attack_rate(self, food_item: str) -> dict:
    """
    2x2 table:
                    Ill     Not Ill
    Ate food        a       b       a/(a+b) = attack rate (exposed)
    Did not eat     c       d       c/(c+d) = attack rate (unexposed)
    
    Risk Ratio = AR_exposed / AR_unexposed
    """
    exposed_ill = sum(1 for c in self.cases 
                      if food_item in c.exposures and c.is_ill)
    exposed_well = sum(1 for c in self.cases 
                       if food_item in c.exposures and not c.is_ill)
    unexposed_ill = sum(1 for c in self.cases 
                        if food_item not in c.exposures and c.is_ill)
    unexposed_well = sum(1 for c in self.cases 
                         if food_item not in c.exposures and not c.is_ill)
    
    ar_exposed = exposed_ill / max(exposed_ill + exposed_well, 1)
    ar_unexposed = unexposed_ill / max(unexposed_ill + unexposed_well, 1)
    rr = ar_exposed / max(ar_unexposed, 0.001)
    
    return {
        "food_item": food_item,
        "two_by_two_table": {
            "ate_ill": exposed_ill,
            "ate_not_ill": exposed_well,
            "not_ate_ill": unexposed_ill,
            "not_ate_not_ill": unexposed_well
        },
        "attack_rate_exposed": round(ar_exposed, 3),
        "attack_rate_unexposed": round(ar_unexposed, 3),
        "risk_ratio": round(rr, 2)
    }
```

### LLM Agent System Prompt (for `inference.py`)
```
You are an epidemiologist investigating a disease outbreak.
Follow the CDC's outbreak investigation methodology:

1. First, view the initial alert to understand the situation
2. Request the line list to see case demographics and onset times  
3. Generate an epi curve to understand the temporal pattern
4. Review exposure histories to identify common exposures
5. Calculate attack rates for suspected food items
6. Request lab results to confirm the pathogen
7. If needed, request environmental samples
8. Submit your hypothesis, then your final answer

Think step by step. At each step, consider:
- What is the most informative action I can take next?
- What does the epi curve shape tell me about the source type?
- Which food items have the highest attack rates?
- Do the symptoms match a specific pathogen profile?
```

---

## 8. Resource Estimates

| Resource | Estimate |
|---|---|
| RAM at runtime | ~80-120 MB (all JSON in memory) |
| Disk for data files | ~2 MB total |
| Docker image size | ~200 MB (Python + deps) |
| Time per episode (easy) | 30-60 seconds |
| Time per episode (hard) | 2-5 minutes |
| Total inference (3 tasks) | 5-15 minutes |
| External dependencies | None (pure Python + Pydantic + FastAPI) |

---

## 9. Why This Wins

1. **Real-world utility (30%)**: CDC's actual investigation workflow, used thousands of times yearly
2. **Task quality (25%)**: Fully deterministic grading, no subjective judgment, clean difficulty progression
3. **Environment design (20%)**: Natural information-gating, dense reward, clean state management
4. **Code quality (15%)**: Pure Python, typed models, Docker-ready, follows OpenEnv spec exactly
5. **Creativity (10%)**: Zero existing RL environments cover investigative epidemiology

**Post-COVID, every judge immediately understands why this matters.** And the investigation metaphor is the perfect fit for LLM agents — it's literally "read text, reason about patterns, decide what to look at next."
