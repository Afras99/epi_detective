# Pathogen Knowledge Base Reference

> All data sourced from CDC "Confirming an Etiology" tables, FDA Bad Bug Book (2nd Edition), and Chai et al. (2019) incubation period study (PMC6805792). This file documents every pathogen in `data/pathogens.json`.

## Data sources

1. **CDC Etiology Tables**: https://www.cdc.gov/foodborne-outbreaks/php/confirming-cause/index.html
2. **FDA Bad Bug Book**: https://www.fda.gov/food/foodborne-pathogens/bad-bug-book-second-edition
3. **FDA Organism Chart**: https://www.fda.gov/media/77727/download
4. **Chai et al. (2019)**: "Incubation periods of enteric illnesses in foodborne outbreaks, US 1998-2013" — PMC6805792
5. **NORS/BEAM Dashboard**: https://wwwn.cdc.gov/norsdashboard/

---

## Category 1: Bacterial — Short Incubation (Toxin-Mediated)

These pathogens cause illness via preformed toxins or rapid toxin production. Short incubation = key diagnostic clue on epi curve.

### Staphylococcus aureus (Staphylococcal food poisoning)

| Field | Value |
|-------|-------|
| **Type** | Bacterial intoxication (preformed enterotoxin) |
| **Incubation** | Median: 3h | Range: 1-6h | 70% range: 2-4h |
| **Symptoms** | Nausea (90%), vomiting (82%), abdominal cramps (75%), diarrhea (68%) |
| **Fever** | Usually absent or low-grade |
| **Duration** | 24-48 hours |
| **Common foods** | Ham, poultry, egg salads, cream pastries, dairy, potato salad |
| **Contamination mechanism** | Human handler (skin, nose, infected wounds) → inadequate refrigeration |
| **Attack rate range** | 0.40-0.80 (high because toxin is preformed) |
| **Lab confirmation** | Detection of enterotoxin in food OR isolation of ≥10⁵ CFU/g S. aureus |
| **Seasonality** | Year-round, slight summer peak |
| **Key diagnostic clue** | Very short incubation + vomiting-predominant + no fever |
| **Synonyms for grader** | `["staphylococcus_aureus", "s_aureus", "staph", "staph_aureus", "staphylococcal"]` |

### Bacillus cereus — Emetic type

| Field | Value |
|-------|-------|
| **Type** | Bacterial intoxication (cereulide toxin, preformed) |
| **Incubation** | Median: 2.5h | Range: 0.5-6h |
| **Symptoms** | Nausea (95%), vomiting (90%), abdominal cramps (40%) |
| **Fever** | Absent |
| **Duration** | 6-24 hours |
| **Common foods** | Fried rice, pasta, starchy foods left at room temp |
| **Contamination mechanism** | Spores survive cooking → germinate during improper cooling |
| **Attack rate range** | 0.30-0.70 |
| **Lab confirmation** | Isolation of ≥10⁵ CFU/g B. cereus from food |
| **Key diagnostic clue** | Very short incubation + rice/starchy food + vomiting dominant |
| **Synonyms** | `["bacillus_cereus", "b_cereus", "bacillus_cereus_emetic"]` |

### Bacillus cereus — Diarrheal type

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection/intoxication (enterotoxin produced in gut) |
| **Incubation** | Median: 10h | Range: 8-16h |
| **Symptoms** | Diarrhea (95%), abdominal cramps (75%), nausea (25%) |
| **Fever** | Absent |
| **Duration** | 12-24 hours |
| **Common foods** | Meats, vegetables, soups, sauces, milk products |
| **Attack rate range** | 0.25-0.55 |
| **Lab confirmation** | Isolation of ≥10⁵ CFU/g B. cereus from food |
| **Key diagnostic clue** | Medium incubation + diarrhea dominant (no vomiting) + meat/vegetables |
| **Synonyms** | `["bacillus_cereus_diarrheal", "b_cereus_diarrheal"]` |

### Clostridium perfringens

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection (enterotoxin produced during sporulation in gut) |
| **Incubation** | Median: 10h | Range: 7-15h | 70% range: 8-14h |
| **Symptoms** | Diarrhea (watery, 95%), abdominal cramps (85%), nausea (25%) |
| **Fever** | Usually absent |
| **Duration** | 24-48 hours |
| **Common foods** | Meats (beef, poultry), gravies, stews — especially large-batch cooked then held warm |
| **Contamination mechanism** | Spores survive cooking → germinate during slow cooling or warm holding |
| **Attack rate range** | 0.40-0.75 |
| **Lab confirmation** | Isolation of ≥10⁶ CFU/g from food OR ≥10⁶ spores/g feces from ill persons |
| **Key diagnostic clue** | Medium incubation + meat/gravy + large batch cooking (cafeterias, catering) |
| **Synonyms** | `["clostridium_perfringens", "c_perfringens", "perfringens"]` |

---

## Category 2: Bacterial — Medium Incubation (Infection)

### Salmonella (non-typhoidal)

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection |
| **Incubation** | Median: 24h | Range: 6-72h | 70% range: 15-65h |
| **Common serotypes** | Typhimurium, Enteritidis, Newport, Heidelberg, Javiana |
| **Symptoms** | Diarrhea (93%), abdominal cramps (82%), fever (72%), nausea (55%), vomiting (40%), headache (35%) |
| **Fever** | YES — key differentiator from toxin-mediated illness |
| **Duration** | 4-7 days |
| **Common foods** | Poultry (chicken, turkey), eggs, produce, pork, beef, raw milk |
| **Attack rate range** | 0.30-0.65 |
| **Lab confirmation** | Culture isolation from clinical specimen or CIDT positive |
| **Seasonality** | Summer/fall peak |
| **Key diagnostic clue** | ~24h incubation + diarrhea WITH fever + poultry/eggs |
| **Synonyms** | `["salmonella", "salmonella_enterica", "salmonella_spp", "salmonellosis", "salmonella_typhimurium", "salmonella_enteritidis", "s_typhimurium", "s_enteritidis"]` |

### Escherichia coli O157:H7 (STEC/EHEC)

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection (Shiga toxin-producing) |
| **Incubation** | Median: 72h | Range: 24-168h (1-7 days) |
| **Symptoms** | Diarrhea (initially watery → bloody, 90%), severe abdominal cramps (85%), nausea (35%) |
| **Fever** | Usually LOW-GRADE or absent |
| **Duration** | 5-10 days |
| **Complications** | HUS (hemolytic uremic syndrome) in ~5-10% of cases — life threatening |
| **Common foods** | Undercooked ground beef, raw milk, leafy greens (lettuce, spinach), raw flour, sprouts |
| **Attack rate range** | 0.15-0.45 |
| **Lab confirmation** | Isolation of E. coli O157:H7 or STEC from stool |
| **Key diagnostic clue** | Bloody diarrhea + no/low fever + ground beef or leafy greens |
| **Synonyms** | `["e_coli_o157", "e_coli", "stec", "ehec", "o157", "e_coli_o157h7", "shiga_toxin_producing"]` |

### Campylobacter jejuni

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection |
| **Incubation** | Median: 48-72h | Range: 24-120h |
| **Symptoms** | Diarrhea (often bloody, 90%), abdominal cramps (severe, 85%), fever (75%), malaise (60%) |
| **Duration** | 2-5 days, can relapse |
| **Complications** | Guillain-Barré syndrome (rare but serious) |
| **Common foods** | Undercooked poultry, raw milk, contaminated water |
| **Attack rate range** | 0.25-0.50 |
| **Lab confirmation** | Culture isolation or CIDT positive |
| **Key diagnostic clue** | 2-3 day incubation + bloody diarrhea + fever + poultry/raw milk |
| **Synonyms** | `["campylobacter", "campylobacter_jejuni", "c_jejuni", "campylobacteriosis"]` |

### Shigella

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection (mucosal invasion) |
| **Incubation** | Median: 36h | Range: 12-96h | LONGEST 70% range among common pathogens |
| **Symptoms** | Diarrhea (often bloody/mucoid, 90%), fever (85%), abdominal cramps (80%), tenesmus (60%) |
| **Duration** | 4-7 days |
| **Common foods** | Salads, raw vegetables, contaminated water — PRIMARILY person-to-person |
| **Attack rate range** | 0.35-0.70 (very low infectious dose) |
| **Lab confirmation** | Culture isolation from stool |
| **Key diagnostic clue** | Bloody/mucoid diarrhea + high fever + daycare/institutional setting |
| **Synonyms** | `["shigella", "shigella_sonnei", "shigella_flexneri", "shigellosis"]` |

### Vibrio parahaemolyticus

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection |
| **Incubation** | Median: 15h | Range: 4-96h | Notably SHORT 70% range (10h) |
| **Symptoms** | Diarrhea (watery, 92%), abdominal cramps (80%), nausea (70%), vomiting (52%), fever (45%) |
| **Duration** | 2-5 days |
| **Common foods** | Raw or undercooked shellfish (oysters, shrimp, crab), sushi |
| **Attack rate range** | 0.20-0.50 |
| **Lab confirmation** | Culture isolation from stool on TCBS agar |
| **Key diagnostic clue** | Short-to-medium incubation + seafood/shellfish exposure + coastal area |
| **Synonyms** | `["vibrio_parahaemolyticus", "v_parahaemolyticus", "vibrio"]` |

### Yersinia enterocolitica

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection |
| **Incubation** | Median: 96-120h | Range: 24-168h |
| **Symptoms** | Diarrhea (90%), abdominal pain (right lower quadrant — mimics appendicitis, 80%), fever (75%) |
| **Duration** | 1-3 weeks |
| **Common foods** | Undercooked pork (chitterlings), raw milk, contaminated water |
| **Attack rate range** | 0.15-0.40 |
| **Key diagnostic clue** | LONG incubation + right-sided abdominal pain mimicking appendicitis + pork |
| **Synonyms** | `["yersinia", "yersinia_enterocolitica", "y_enterocolitica", "yersiniosis"]` |

---

## Category 3: Bacterial — Long Incubation

### Listeria monocytogenes

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection |
| **Incubation** | VERY LONG: 1-70 days (median ~21 days for invasive disease) |
| **Gastrointestinal form** | Incubation: 24h, diarrhea, fever — milder |
| **Invasive form** | Fever, meningitis, septicemia, miscarriage |
| **Common foods** | Deli meats, soft cheeses, smoked fish, unpasteurized milk, cantaloupe |
| **At-risk populations** | Pregnant women, elderly, immunocompromised, neonates |
| **Attack rate range** | 0.05-0.20 (low attack rate but HIGH mortality ~20-30%) |
| **Lab confirmation** | Culture isolation from blood/CSF |
| **Key diagnostic clue** | Very long incubation + pregnant/elderly/immunocompromised + deli meats/soft cheese |
| **Synonyms** | `["listeria", "listeria_monocytogenes", "l_monocytogenes", "listeriosis"]` |

---

## Category 4: Viral

### Norovirus

| Field | Value |
|-------|-------|
| **Type** | Viral infection — #1 CAUSE OF US FOODBORNE OUTBREAKS |
| **Incubation** | Median: 33h | Range: 12-48h | 70% range: NARROW (10h) — very tight clustering |
| **Symptoms** | Vomiting (78%), diarrhea (watery non-bloody, 72%), nausea (80%), abdominal cramps (62%), low-grade fever (37%) |
| **Duration** | 24-72 hours (self-limiting) |
| **Common foods** | Ready-to-eat foods (salads, sandwiches, bakery items), shellfish, any food handled by infected person |
| **Contamination mechanism** | Infected food handler — NOT the food itself. Also person-to-person |
| **Attack rate range** | 0.40-0.75 (very contagious, low infectious dose ~18 virus particles) |
| **Lab confirmation** | RT-PCR of stool or vomitus |
| **Seasonality** | Winter peak ("winter vomiting disease") |
| **Key diagnostic clue** | Vomiting-predominant + very narrow epi curve peak + food handler source + winter |
| **Synonyms** | `["norovirus", "norwalk_virus", "norwalk", "calicivirus", "noro"]` |

### Hepatitis A

| Field | Value |
|-------|-------|
| **Type** | Viral infection |
| **Incubation** | VERY LONG: 15-50 days (median 28 days) |
| **Symptoms** | Jaundice (yellowing, 70%), fatigue (80%), nausea (70%), abdominal pain (65%), dark urine (65%), fever (55%) |
| **Duration** | Weeks to months |
| **Common foods** | Shellfish, raw produce, any food handled by infected person |
| **Attack rate range** | 0.15-0.40 |
| **Lab confirmation** | IgM anti-HAV positive |
| **Key diagnostic clue** | Very long incubation + jaundice + shellfish or food handler |
| **Synonyms** | `["hepatitis_a", "hep_a", "hav"]` |

### Rotavirus

| Field | Value |
|-------|-------|
| **Type** | Viral infection |
| **Incubation** | 24-72 hours |
| **Symptoms** | Vomiting (80%), watery diarrhea (90%), fever (60%), dehydration (common in children) |
| **Duration** | 3-8 days |
| **Common foods** | Fecal-oral, contaminated water, food handlers |
| **At-risk** | Children under 5 |
| **Attack rate range** | 0.30-0.60 |
| **Key diagnostic clue** | Children predominantly affected + vomiting + watery diarrhea |
| **Synonyms** | `["rotavirus", "rota"]` |

---

## Category 5: Parasitic

### Cyclospora cayetanensis

| Field | Value |
|-------|-------|
| **Type** | Parasitic infection |
| **Incubation** | Median: 7 days | Range: 2-14 days |
| **Symptoms** | Watery diarrhea (95%), loss of appetite (80%), bloating (75%), fatigue (70%), nausea (50%) |
| **Duration** | Days to weeks, can relapse |
| **Common foods** | Imported fresh produce (raspberries, basil, cilantro, lettuce) |
| **Attack rate range** | 0.10-0.35 |
| **Lab confirmation** | Detection of oocysts in stool (modified acid-fast stain) |
| **Key diagnostic clue** | LONG incubation + imported produce + relapsing watery diarrhea + spring/summer |
| **Synonyms** | `["cyclospora", "cyclospora_cayetanensis", "cyclosporiasis"]` |

### Cryptosporidium

| Field | Value |
|-------|-------|
| **Type** | Parasitic infection |
| **Incubation** | 2-10 days (median 7 days) |
| **Symptoms** | Watery diarrhea (profuse, 95%), stomach cramps (80%), dehydration (60%), nausea (50%) |
| **Duration** | 1-3 weeks |
| **Common foods** | Contaminated water (swimming pools, drinking water), unpasteurized cider, raw milk |
| **Key diagnostic clue** | Waterborne + prolonged watery diarrhea + recreational water exposure |
| **Synonyms** | `["cryptosporidium", "crypto", "cryptosporidiosis"]` |

### Trichinella spiralis

| Field | Value |
|-------|-------|
| **Type** | Parasitic infection (larvae encyst in muscle) |
| **Incubation** | 1-2 days (GI phase) → 2-8 weeks (muscle phase) |
| **Symptoms** | Phase 1: diarrhea, abdominal pain. Phase 2: muscle pain, fever, periorbital edema, eosinophilia |
| **Common foods** | Undercooked pork, wild game (bear, boar, walrus) |
| **Key diagnostic clue** | Two-phase illness + muscle pain + periorbital swelling + wild game |
| **Synonyms** | `["trichinella", "trichinella_spiralis", "trichinosis", "trichinellosis"]` |

---

## Category 6: Environmental (Non-foodborne — for Task 2)

### Legionella pneumophila

| Field | Value |
|-------|-------|
| **Type** | Bacterial infection (respiratory — NOT foodborne) |
| **Incubation** | Pontiac fever: 24-48h | Legionnaires' disease: 2-10 days |
| **Symptoms (Legionnaires')** | Pneumonia (90%), high fever (80%), cough (65%), muscle aches (55%), headache (50%), confusion (30%) |
| **Symptoms (Pontiac fever)** | Fever (90%), muscle aches (80%), headache (75%) — NO pneumonia |
| **Duration** | Pontiac: 2-5 days | Legionnaires': weeks, can be fatal |
| **Source** | Cooling towers, hot water systems, fountains, misters, spas |
| **NOT person-to-person** | Cannot spread between people |
| **Attack rate range** | 0.01-0.05 (Legionnaires') or 0.50-0.95 (Pontiac fever) |
| **Lab confirmation** | Urinary antigen test, culture from respiratory specimen |
| **Key diagnostic clue** | Pneumonia cluster + shared building/water system + NOT person-to-person + elderly |
| **Why in Task 2** | Agent must distinguish from concurrent influenza season using symptom profiles + environmental source |
| **Synonyms** | `["legionella", "legionella_pneumophila", "legionnaires", "legionnaires_disease", "pontiac_fever"]` |

---

## Category 7: Marine Toxins (History-Dependent Diagnosis)

### Ciguatoxin

| Field | Value |
|-------|-------|
| **Type** | Toxin (heat-stable, from reef fish) |
| **Incubation** | 1-24 hours (GI symptoms) → neurological symptoms may follow |
| **Symptoms** | GI (diarrhea, vomiting), PLUS: paresthesia, temperature reversal (hot-cold swap), weakness |
| **Common foods** | Large predatory reef fish (barracuda, grouper, snapper, amberjack) |
| **Key diagnostic clue** | Hot-cold temperature reversal is PATHOGNOMONIC + reef fish consumption |
| **Synonyms** | `["ciguatoxin", "ciguatera", "ciguatera_fish_poisoning"]` |

### Scombroid toxin (Histamine)

| Field | Value |
|-------|-------|
| **Type** | Toxin (histamine produced by bacterial action on fish) |
| **Incubation** | Minutes to 1 hour |
| **Symptoms** | Facial flushing (90%), rash (70%), diarrhea (60%), headache (55%), palpitations (40%) |
| **Duration** | 3-6 hours |
| **Common foods** | Tuna, mackerel, mahi-mahi, bluefish — improperly refrigerated |
| **Key diagnostic clue** | IMMEDIATE onset + facial flushing/rash + fish (looks like allergic reaction) |
| **Synonyms** | `["scombroid", "histamine_fish_poisoning", "scombrotoxin"]` |

### Clostridium botulinum (Botulism)

| Field | Value |
|-------|-------|
| **Type** | Toxin (neurotoxin, most potent biological toxin known) |
| **Incubation** | 12-36 hours (range: 6h - 10 days) |
| **Symptoms** | Descending paralysis: blurred vision → difficulty swallowing → muscle weakness → respiratory failure |
| **Common foods** | Home-canned foods, fermented fish, honey (infant), improperly processed canned goods |
| **CRITICAL** | Medical emergency — antitoxin from CDC |
| **Key diagnostic clue** | Descending paralysis + home-canned food + NO fever |
| **Synonyms** | `["botulism", "clostridium_botulinum", "c_botulinum", "botulinum_toxin"]` |

---

## How to use this data in the environment

### For scenario generation:
1. Pick a pathogen from the appropriate pool for the task difficulty
2. Sample food vehicle from the pathogen's `common_foods` list
3. Generate cases using the incubation period distribution (median ± variance)
4. Assign symptoms using the frequency percentages (e.g., 93% of Salmonella cases get diarrhea)
5. Plant ground truth: pathogen + food + route

### For grading:
1. Compare agent's submitted pathogen against `synonyms` list (case-insensitive)
2. Partial credit: correct genus but wrong/missing species = 0.5
3. Source matching also uses synonym sets from `synonym_sets.json`

### For reward shaping:
1. Lab results that identify the pathogen = high information value (+0.25)
2. Attack rate calculation on the correct food = high information value (+0.15)
3. Requesting irrelevant evidence = cost (-0.02)
4. The epi curve shape itself is a clue — tight peaks suggest toxin-mediated (S. aureus, B. cereus), broader curves suggest infection (Salmonella, E. coli)
