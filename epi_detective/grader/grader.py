"""
Deterministic grader for EpiDetective.

Scores a final submission against the scenario's planted ground truth
across 5 components, each reflecting a real public health deliverable:

  Component                  Weight  What it measures
  ─────────────────────────────────────────────────────────────────────
  Pathogen identification      25%   Correct organism (fuzzy matching)
  Food source identification   25%   Correct vehicle (fuzzy matching)
  Transmission route           20%   Correct route
  Case definition quality      15%   Clinical + time + place criteria
  Step efficiency              15%   Fewer steps = higher bonus

Pathogen and source matching uses normalised fuzzy matching so common
synonyms (e.g. "salmonellosis", "S. typhimurium") all match "salmonella".

EpiGrader.grade() returns a float strictly in (0.001, 0.999).
compute_step_reward() returns dense per-step rewards to encourage
systematic evidence gathering rather than random guessing.
"""
import json


class EpiGrader:
    def _grade_multi_outbreak(
        self, submission, ground_truth, steps_taken, optimal_steps, max_steps
    ):
        """Hard task: grade against both outbreaks, use best per component."""
        best = {"pathogen": 0.0, "source": 0.0, "route": 0.0}

        for outbreak_key in ("outbreak_a", "outbreak_b"):
            ob = ground_truth[outbreak_key]
            best["pathogen"] = max(
                best["pathogen"],
                self._grade_pathogen(
                    submission.get("pathogen", ""),
                    ob["pathogen"],
                    ob.get("pathogen_synonyms", []),
                ),
            )
            best["source"] = max(
                best["source"],
                self._grade_source(
                    submission.get("source", ""),
                    ob["source"],
                    ob.get("source_synonyms", []),
                ),
            )
            best["route"] = max(
                best["route"],
                self._grade_route(submission.get("route", ""), ob["route"]),
            )

        case_def = submission.get("case_definition", {})
        eff = self._grade_efficiency(steps_taken, optimal_steps, max_steps)
        score = (
            0.25 * best["pathogen"] +
            0.25 * best["source"] +
            0.20 * best["route"] +
            0.15 * self._grade_case_definition(case_def) +
            0.15 * eff
        )
        return round(min(max(score, 0.001), 0.999), 4)

    def grade(
        self,
        submission: dict,
        ground_truth: dict,
        steps_taken: int,
        optimal_steps: int,
        max_steps: int,
    ) -> float:
        """Grade a final submission. Returns float in (0.001, 0.999)."""
        if ground_truth.get("type") == "multi_outbreak":
            return self._grade_multi_outbreak(
                submission, ground_truth, steps_taken, optimal_steps, max_steps
            )

        score = 0.0

        # 1. Pathogen identification (0.25)
        score += 0.25 * self._grade_pathogen(
            submission.get("pathogen", ""),
            ground_truth["pathogen"],
            ground_truth.get("pathogen_synonyms", []),
        )

        # 2. Source identification (0.25)
        score += 0.25 * self._grade_source(
            submission.get("source", ""),
            ground_truth["source"],
            ground_truth.get("source_synonyms", []),
        )

        # 3. Transmission route (0.20)
        score += 0.20 * self._grade_route(
            submission.get("route", ""),
            ground_truth["route"],
        )

        # 4. Case definition quality (0.15)
        score += 0.15 * self._grade_case_definition(
            submission.get("case_definition", {})
        )

        # 5. Efficiency (0.15)
        score += 0.15 * self._grade_efficiency(
            steps_taken, optimal_steps, max_steps
        )

        # Score must be strictly between 0 and 1 (exclusive) per validator spec
        return round(min(max(score, 0.001), 0.999), 4)

    def _grade_pathogen(self, submitted, correct, synonyms):
        sub = self._normalize(submitted)
        if sub == self._normalize(correct):
            return 1.0
        for syn in synonyms:
            if sub == self._normalize(syn):
                return 1.0
        # Partial credit: correct genus
        correct_genus = correct.split("_")[0]
        if correct_genus in sub:
            return 0.5
        return 0.0

    def _grade_source(self, submitted, correct, synonyms):
        sub = self._normalize(submitted)
        if sub == self._normalize(correct):
            return 1.0
        for syn in synonyms:
            if sub == self._normalize(syn):
                return 1.0
        # Partial credit: food category match
        if self._normalize(correct).replace("_", "") in sub.replace("_", ""):
            return 0.5
        return 0.0

    def _grade_route(self, submitted, correct):
        sub = self._normalize(submitted)
        correct_norm = self._normalize(correct)
        if sub == correct_norm:
            return 1.0
        aliases = {
            "foodborne": [
                "foodborne", "food_borne", "food-borne", "food",
            ],
            "waterborne": ["waterborne", "water_borne", "water"],
            "person_to_person": [
                "person_to_person", "person-to-person", "p2p", "fecal_oral",
            ],
            "environmental_airborne": [
                "environmental_airborne", "airborne",
                "environmental", "aerosol",
            ],
            "animal_contact": ["animal_contact", "animal", "zoonotic"],
        }
        for canonical, alias_list in aliases.items():
            if correct_norm in alias_list or canonical == correct_norm:
                if sub in alias_list or sub == canonical:
                    return 1.0
        return 0.0

    def _grade_case_definition(self, case_def):
        if not case_def or not isinstance(case_def, dict):
            return 0.0

        trivial = {
            "unknown", "n/a", "na", "none", "tbd", "?",
            "not specified", "unclear",
        }

        def meaningful(val):
            """True only if value is a non-trivial, informative string."""
            if not val:
                return False
            v = str(val).lower().strip()
            return len(v) >= 1 and not any(t in v for t in trivial)

        score = 0.0
        # Clinical criteria (symptoms, organism) — 40%
        if meaningful(case_def.get("clinical")) or meaningful(
            case_def.get("symptoms")
        ):
            score += 0.40
        # Time criteria (onset window, incubation period) — 30%
        if (meaningful(case_def.get("time"))
                or meaningful(case_def.get("onset"))):
            score += 0.30
        # Place/exposure criteria (venue, food, event) — 30%
        if (meaningful(case_def.get("place"))
                or meaningful(case_def.get("exposure"))
                or meaningful(case_def.get("location"))):
            score += 0.30
        return score

    def _grade_efficiency(self, steps_taken, optimal, maximum):
        if steps_taken <= optimal:
            return 1.0
        if steps_taken >= maximum:
            return 0.0
        return 1.0 - (steps_taken - optimal) / (maximum - optimal)

    def _normalize(self, text):
        return str(text).lower().strip().replace(" ", "_").replace("-", "_")


def compute_step_reward(
    command: str,
    parameters: dict,
    action_history: set,
    ground_truth: dict,
) -> float:
    """Dense per-step reward."""
    action_key = f"{command}:{json.dumps(parameters, sort_keys=True)}"
    if action_key in action_history:
        return -0.02  # Redundant action penalty

    EVIDENCE_REWARDS = {
        "view_initial_alert": 0.02,
        "request_line_list": 0.05,
        "generate_epi_curve": 0.03,
        "get_exposure_history": 0.05,
        "request_lab_results": 0.08,
        "calculate_attack_rate": 0.05,
        "calculate_odds_ratio": 0.04,
        "request_environmental_samples": 0.04,
    }

    if command in EVIDENCE_REWARDS:
        base = EVIDENCE_REWARDS[command]
        # Bonus if investigating the correct food source
        if command == "calculate_attack_rate":
            food = parameters.get("food_item", "")
            gt_source = ground_truth["source"].lower()
            if food.lower().replace(" ", "_") == gt_source:
                base += 0.05
        return base

    if command == "submit_hypothesis":
        return 0.0  # Feedback only, no reward

    return 0.0
