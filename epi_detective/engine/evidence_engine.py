"""
Evidence engine for EpiDetective.

Implements information gating — the agent can only learn facts about the outbreak
by explicitly requesting them through investigation commands, just as a real
field epidemiologist must physically request lab results, interview patients,
and order environmental swabs.

Each handler corresponds to a real investigative action from the CDC 13-step
outbreak investigation protocol:

  view_initial_alert           → Step 1: Verify the outbreak exists
  request_line_list            → Step 2: Define and find cases
  generate_epi_curve           → Step 3: Describe cases by time
  request_lab_results          → Step 4: Confirm diagnosis with lab data
  get_exposure_history         → Step 5: Describe cases by person/place
  calculate_attack_rate        → Step 6: Develop hypotheses (2×2 table)
  calculate_odds_ratio         → Step 6: Test hypotheses (OR analysis)
  request_environmental_samples → Step 7: Environmental investigation
  submit_hypothesis            → Step 8: Test theory (partial feedback only)
  submit_final_answer          → Steps 9-13: Implement control + report

Rewards are given for new evidence. Repeating the same action incurs -0.02.
"""
import json
from collections import Counter


class EvidenceEngine:
    def __init__(self, scenario):
        self.scenario = scenario
        self.unlocked = {"initial_alert"}
        self.action_history = set()
        self.hypothesis_count = 0

    def process_action(self, command: str, parameters: dict) -> dict:
        """Process an agent action and return observation data."""
        action_key = f"{command}:{json.dumps(parameters, sort_keys=True)}"
        is_repeat = action_key in self.action_history
        self.action_history.add(action_key)

        handlers = {
            "view_initial_alert": self._handle_alert,
            "request_line_list": self._handle_line_list,
            "generate_epi_curve": self._handle_epi_curve,
            "request_lab_results": self._handle_lab_results,
            "get_exposure_history": self._handle_exposure_history,
            "calculate_attack_rate": self._handle_attack_rate,
            "calculate_odds_ratio": self._handle_odds_ratio,
            "request_environmental_samples": self._handle_environmental,
            "submit_hypothesis": self._handle_hypothesis,
        }

        handler = handlers.get(command)
        if handler:
            result = handler(parameters)
            result["is_repeat"] = is_repeat
            return result
        else:
            return {
                "result_type": "error",
                "data": {},
                "narrative": f"Unknown command: {command}. Available commands: {', '.join(handlers.keys())}, submit_final_answer",
                "is_repeat": False,
            }

    def _handle_alert(self, params):
        return {
            "result_type": "alert",
            "data": {"task_id": self.scenario.task_id, "setting": self.scenario.setting_key},
            "narrative": self.scenario.initial_alert,
        }

    def _handle_line_list(self, params):
        self.unlocked.add("line_list")
        ill = self.scenario.ill_people
        data = []
        for p in ill:
            data.append({
                "case_id": p["case_id"],
                "name": p["name"],
                "age": p["age"],
                "sex": p["sex"],
                "onset_datetime": p["onset_datetime"],
                "symptoms": p["symptoms"],
                "hospitalized": p["hospitalized"],
            })
        narrative = (
            f"Line list received: {len(data)} cases identified.\n"
            f"Age range: {min(p['age'] for p in ill)}-{max(p['age'] for p in ill)} years.\n"
            f"Sex distribution: {sum(1 for p in ill if p['sex']=='M')} male, "
            f"{sum(1 for p in ill if p['sex']=='F')} female.\n"
            f"Hospitalizations: {sum(1 for p in ill if p['hospitalized'])}.\n"
            f"Most common symptoms: {self._top_symptoms(ill)}"
        )
        return {"result_type": "line_list", "data": {"cases": data}, "narrative": narrative}

    def _handle_epi_curve(self, params):
        self.unlocked.add("epi_curve")
        grouping = params.get("grouping", "hour")
        ill = self.scenario.ill_people
        onsets = [p["onset_datetime"] for p in ill if p["onset_datetime"]]
        onsets.sort()

        if grouping == "hour":
            # Group by hour offset from first case
            from datetime import datetime
            parsed = [datetime.fromisoformat(o) for o in onsets]
            if not parsed:
                return {"result_type": "epi_curve", "data": {}, "narrative": "No onset data available."}
            base = min(parsed)
            bins = Counter()
            for dt in parsed:
                hour = int((dt - base).total_seconds() / 3600)
                bins[hour] = bins.get(hour, 0) + 1
            curve_data = {str(h): c for h, c in sorted(bins.items())}
            if not bins:
                return {"result_type": "epi_curve", "data": {}, "narrative": "No onset data available."}
            total_hours = max(bins.keys()) - min(bins.keys())
            peak_hour = max(bins, key=bins.get)
        else:
            curve_data = {}
            total_hours = 0
            peak_hour = 0

        narrative = (
            f"Epi curve generated ({grouping} grouping): {len(onsets)} cases plotted.\n"
            f"Onset span: {total_hours} hours from first to last case.\n"
            f"Peak at hour {peak_hour} with {bins.get(peak_hour, 0)} cases.\n"
            f"Curve shape suggests {'a point-source exposure' if total_hours < 72 else 'a propagated or continuous source'}."
        )
        return {"result_type": "epi_curve", "data": {"curve": curve_data, "grouping": grouping}, "narrative": narrative}

    def _handle_lab_results(self, params):
        self.unlocked.add("lab_results")
        case_ids = params.get("case_ids", [])
        if not case_ids:
            case_ids = list(self.scenario.lab_results.keys())[:10]

        results = {}
        for cid in case_ids:
            if cid in self.scenario.lab_results:
                results[cid] = self.scenario.lab_results[cid]
            else:
                results[cid] = {"result": "NOT_TESTED", "organism": None}

        positive = [r for r in results.values() if r["result"] == "POSITIVE"]
        organisms = Counter(r.get("organism", "Unknown") for r in positive)
        top_org = organisms.most_common(1)[0] if organisms else ("None identified", 0)

        narrative = (
            f"Lab results for {len(case_ids)} cases: "
            f"{len(positive)} positive, "
            f"{sum(1 for r in results.values() if r['result'] == 'PENDING')} pending, "
            f"{sum(1 for r in results.values() if r['result'] == 'NOT_TESTED')} not tested.\n"
            f"Most common organism identified: {top_org[0]} ({top_org[1]} cases)."
        )
        return {"result_type": "lab_results", "data": {"results": results}, "narrative": narrative}

    def _handle_exposure_history(self, params):
        self.unlocked.add("exposure_history")
        case_ids = params.get("case_ids", [])
        if not case_ids:
            case_ids = [p["case_id"] for p in self.scenario.ill_people[:15]]

        histories = {}
        for cid in case_ids:
            if cid in self.scenario.exposure_matrix:
                histories[cid] = {
                    food: "Yes" if ate else "No"
                    for food, ate in self.scenario.exposure_matrix[cid].items()
                }

        # Summarize food exposure frequencies
        food_counts = Counter()
        for hist in histories.values():
            for food, ate in hist.items():
                if ate == "Yes":
                    food_counts[food] += 1

        top_foods = food_counts.most_common(5)
        food_summary = ", ".join(f"{f.replace('_', ' ')} ({c}/{len(histories)})" for f, c in top_foods)

        narrative = (
            f"Exposure histories obtained for {len(histories)} cases.\n"
            f"Foods most commonly consumed by cases: {food_summary}.\n"
            f"Menu items available at the event: {', '.join(f.replace('_', ' ') for f in self.scenario.menu_items)}."
        )
        return {"result_type": "exposure_history", "data": {"histories": histories}, "narrative": narrative}

    def _handle_attack_rate(self, params):
        food_item = params.get("food_item", "")
        if "exposure_history" not in self.unlocked:
            return {
                "result_type": "error",
                "data": {},
                "narrative": "You must first gather exposure histories using get_exposure_history before running attack rate analysis.",
            }
        if food_item not in self.scenario.menu_items:
            return {
                "result_type": "attack_rate",
                "data": {},
                "narrative": f"Food item '{food_item}' not found in exposure data. Available: {', '.join(self.scenario.menu_items)}",
            }

        ill_ids = {p["case_id"] for p in self.scenario.ill_people}
        ate_ill = ate_well = not_ate_ill = not_ate_well = 0
        for cid, exposures in self.scenario.exposure_matrix.items():
            ate = exposures.get(food_item, False)
            ill = cid in ill_ids
            if ate and ill: ate_ill += 1
            elif ate and not ill: ate_well += 1
            elif not ate and ill: not_ate_ill += 1
            else: not_ate_well += 1

        ar_ate = ate_ill / (ate_ill + ate_well) if (ate_ill + ate_well) > 0 else 0
        ar_not = not_ate_ill / (not_ate_ill + not_ate_well) if (not_ate_ill + not_ate_well) > 0 else 0
        rr = ar_ate / ar_not if ar_not > 0 else 99.0

        data = {
            "food_item": food_item,
            "ate_ill": ate_ill, "ate_well": ate_well,
            "not_ate_ill": not_ate_ill, "not_ate_well": not_ate_well,
            "attack_rate_ate": round(ar_ate, 3),
            "attack_rate_not_ate": round(ar_not, 3),
            "relative_risk": round(rr, 2),
        }
        narrative = (
            f"Attack rate for {food_item.replace('_', ' ')}:\n"
            f"  Ate and ill: {ate_ill}, Ate and well: {ate_well} → Attack rate: {ar_ate:.1%}\n"
            f"  Did not eat and ill: {not_ate_ill}, Did not eat and well: {not_ate_well} → Attack rate: {ar_not:.1%}\n"
            f"  Relative risk: {rr:.2f}"
        )
        return {"result_type": "attack_rate", "data": data, "narrative": narrative}

    def _handle_odds_ratio(self, params):
        food_item = params.get("exposure", params.get("food_item", ""))
        # Reuse attack rate logic
        ar_result = self._handle_attack_rate({"food_item": food_item})
        d = ar_result["data"]
        if not d:
            ar_result["result_type"] = "odds_ratio"
            return ar_result

        a, b, c, d_val = d["ate_ill"], d["ate_well"], d["not_ate_ill"], d["not_ate_well"]
        odds_ratio = (a * d_val) / (b * c) if (b * c) > 0 else 99.0

        return {
            "result_type": "odds_ratio",
            "data": {**d, "odds_ratio": round(odds_ratio, 2)},
            "narrative": f"Odds ratio for {food_item.replace('_', ' ')}: {odds_ratio:.2f} "
                         f"(>1 suggests association between exposure and illness)",
        }

    def _handle_environmental(self, params):
        self.unlocked.add("environmental")
        location = params.get("location", "kitchen")
        gt = self.scenario.ground_truth

        # Environmental samples confirm the source if location is relevant
        found = False
        if gt["route"] in ("foodborne",) and "kitchen" in location.lower():
            found = True
        if gt.get("type") == "multi_outbreak":
            found = True

        if found:
            narrative = (
                f"Environmental samples collected from {location}.\n"
                f"Result: {gt.get('pathogen_full_name', gt['pathogen'])} "
                f"detected in food preparation area. "
                f"Samples from {gt.get('source_display_name', gt['source'])} tested POSITIVE."
            )
        else:
            narrative = f"Environmental samples collected from {location}. No significant findings."

        return {
            "result_type": "environmental",
            "data": {"location": location, "pathogen_found": found},
            "narrative": narrative,
        }

    def _handle_hypothesis(self, params):
        self.hypothesis_count += 1
        if self.hypothesis_count > 3:
            return {
                "result_type": "error",
                "data": {},
                "narrative": "Maximum hypothesis attempts (3) reached. You must now submit your final answer.",
            }

        gt = self.scenario.ground_truth
        pathogen_correct = self._fuzzy_match(params.get("pathogen", ""), gt["pathogen"], gt.get("pathogen_synonyms", []))
        source_correct = self._fuzzy_match(params.get("source", ""), gt["source"], gt.get("source_synonyms", []))
        route_correct = params.get("route", "").lower().strip() == gt["route"].lower()

        score = (0.4 if pathogen_correct else 0.0) + (0.4 if source_correct else 0.0) + (0.2 if route_correct else 0.0)

        attempts_left = 3 - self.hypothesis_count
        narrative = (
            f"Hypothesis evaluation ({self.hypothesis_count}/3 attempts used, {attempts_left} remaining):\n"
            f"  Pathogen: {'✓ Correct' if pathogen_correct else '✗ Incorrect'}\n"
            f"  Source:   {'✓ Correct' if source_correct else '✗ Incorrect'}\n"
            f"  Route:    {'✓ Correct' if route_correct else '✗ Incorrect'}\n"
            f"  Overall match: {score:.0%}"
        )
        return {
            "result_type": "hypothesis_feedback",
            "data": {
                "pathogen_correct": pathogen_correct,
                "source_correct": source_correct,
                "route_correct": route_correct,
                "partial_score": score,
                "attempts_remaining": attempts_left,
            },
            "narrative": narrative,
        }

    def _fuzzy_match(self, submitted, correct, synonyms):
        sub = submitted.lower().strip().replace(" ", "_").replace("-", "_")
        if sub == correct.lower():
            return True
        for syn in synonyms:
            if sub == syn.lower().replace(" ", "_").replace("-", "_"):
                return True
        return False

    def _top_symptoms(self, ill_people):
        symptom_counts = Counter()
        for p in ill_people:
            for s in p.get("symptoms", []):
                symptom_counts[s] += 1
        top = symptom_counts.most_common(4)
        return ", ".join(f"{s.replace('_', ' ')} ({c}/{len(ill_people)})" for s, c in top)
