"""
Core tests for EpiDetective — grader, scenario generator, and evidence engine.
Run with: uv run pytest tests/test_core.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from grader.grader import EpiGrader
from engine.scenario_generator import ScenarioGenerator


class TestGrader:
    def setup_method(self):
        self.grader = EpiGrader()
        self.gt = {
            "pathogen": "salmonella",
            "pathogen_synonyms": ["salmonella_enterica", "salmonellosis"],
            "source": "chicken",
            "source_synonyms": ["chicken_breast", "poultry"],
            "route": "foodborne",
        }

    def _grade(self, sub):
        return self.grader.grade(sub, self.gt, steps_taken=8, optimal_steps=8, max_steps=15)

    def test_perfect_score_clamped_below_1(self):
        score = self._grade({"pathogen": "salmonella", "source": "chicken", "route": "foodborne",
                              "case_definition": {"clinical": "diarrhea", "time": "6-72h", "place": "venue"}})
        assert score < 1.0
        assert score > 0.8

    def test_all_wrong_clamped_above_0(self):
        score = self._grade({"pathogen": "unknown", "source": "unknown", "route": "waterborne", "case_definition": {}})
        assert score > 0.0
        assert score < 0.3

    def test_pathogen_synonym_match(self):
        score = self._grade({"pathogen": "salmonella_enterica", "source": "chicken", "route": "foodborne",
                              "case_definition": {"clinical": "x", "time": "x", "place": "x"}})
        assert score > 0.8

    def test_partial_pathogen_genus_match(self):
        # "salmonella" genus in submitted text
        partial = self.grader._grade_pathogen("salmonella_typhi", "salmonella", ["salmonella_enterica"])
        assert partial == 0.5

    def test_route_alias_match(self):
        assert self.grader._grade_route("food-borne", "foodborne") == 1.0
        assert self.grader._grade_route("food_borne", "foodborne") == 1.0
        assert self.grader._grade_route("waterborne", "foodborne") == 0.0

    def test_case_definition_partial_credit(self):
        # Only clinical
        assert self.grader._grade_case_definition({"clinical": "diarrhea"}) == 0.40
        # Clinical + time
        assert self.grader._grade_case_definition({"clinical": "diarrhea", "time": "24h"}) == 0.70
        # All three
        assert self.grader._grade_case_definition({"clinical": "x", "time": "x", "place": "x"}) == 1.0

    def test_efficiency_at_optimal(self):
        assert self.grader._grade_efficiency(8, 8, 15) == 1.0

    def test_efficiency_at_max(self):
        assert self.grader._grade_efficiency(15, 8, 15) == 0.0

    def test_efficiency_midpoint(self):
        eff = self.grader._grade_efficiency(11, 8, 15)
        assert 0.0 < eff < 1.0

    def test_score_always_in_range(self):
        for sub in [
            {},
            {"pathogen": "salmonella", "source": "chicken", "route": "foodborne"},
            {"pathogen": "wrong", "source": "wrong", "route": "wrong", "case_definition": {"clinical": "x", "time": "x", "place": "x"}},
        ]:
            score = self._grade(sub)
            assert 0.0 < score < 1.0

    def test_multi_outbreak_grading(self):
        gt_multi = {
            "type": "multi_outbreak",
            "outbreak_a": {
                "pathogen": "salmonella", "pathogen_synonyms": [],
                "source": "chicken", "source_synonyms": [],
                "route": "foodborne",
            },
            "outbreak_b": {
                "pathogen": "norovirus", "pathogen_synonyms": ["norwalk_virus"],
                "source": "romaine_lettuce", "source_synonyms": [],
                "route": "foodborne",
            },
            "pathogen": "salmonella", "pathogen_synonyms": [],
            "source": "chicken", "source_synonyms": [],
            "route": "foodborne",
        }
        # Identifying outbreak_b should still give a high score
        score = self.grader.grade(
            {"pathogen": "norovirus", "source": "romaine_lettuce", "route": "foodborne",
             "case_definition": {"clinical": "x", "time": "x", "place": "x"}},
            gt_multi, steps_taken=10, optimal_steps=20, max_steps=35
        )
        assert score > 0.5  # should get credit for identifying one outbreak


class TestScenarioGenerator:
    def setup_method(self):
        self.gen = ScenarioGenerator()

    def test_determinism(self):
        s1 = self.gen.generate("easy", seed=42)
        s2 = self.gen.generate("easy", seed=42)
        assert s1.ground_truth == s2.ground_truth
        assert s1.initial_alert == s2.initial_alert
        assert len(s1.people) == len(s2.people)

    def test_different_seeds_differ(self):
        s1 = self.gen.generate("easy", seed=1)
        s2 = self.gen.generate("easy", seed=2)
        # Very likely to be different
        assert s1.ground_truth != s2.ground_truth or s1.initial_alert != s2.initial_alert

    def test_ground_truth_required_fields(self):
        for task in ["easy", "medium", "hard"]:
            s = self.gen.generate(task, seed=99)
            gt = s.ground_truth
            assert "pathogen" in gt
            assert "source" in gt or gt.get("type") == "multi_outbreak"
            assert "route" in gt

    def test_exposure_matrix_covers_all_menu_items(self):
        s = self.gen.generate("easy", seed=42)
        for person in s.people:
            cid = person["case_id"]
            assert cid in s.exposure_matrix
            for food in s.menu_items:
                assert food in s.exposure_matrix[cid], f"{food} missing for {cid}"

    def test_ill_people_have_symptoms(self):
        s = self.gen.generate("easy", seed=42)
        for p in s.ill_people:
            assert len(p["symptoms"]) > 0

    def test_menu_contains_guilty_food(self):
        s = self.gen.generate("easy", seed=42)
        assert s.food_vehicle_key in s.menu_items

    def test_all_tasks_generate(self):
        for task in ["easy", "medium", "hard"]:
            s = self.gen.generate(task, seed=77)
            assert s is not None
            assert len(s.people) > 0
            assert s.initial_alert


class TestEvidenceEngine:
    def setup_method(self):
        from engine.evidence_engine import EvidenceEngine
        gen = ScenarioGenerator()
        self.scenario = gen.generate("easy", seed=42)
        self.engine = EvidenceEngine(self.scenario)

    def test_repeat_action_detected(self):
        self.engine.process_action("view_initial_alert", {})
        result = self.engine.process_action("view_initial_alert", {})
        assert result["is_repeat"] is True

    def test_attack_rate_requires_exposure_history_first(self):
        # Should fail without exposure history
        result = self.engine.process_action("calculate_attack_rate", {"food_item": self.scenario.menu_items[0]})
        assert result["result_type"] == "error"

        # Unlock exposure history
        self.engine.process_action("get_exposure_history", {})

        # Now should work
        result = self.engine.process_action("calculate_attack_rate", {"food_item": self.scenario.menu_items[0]})
        assert result["result_type"] == "attack_rate"

    def test_attack_rate_invalid_food(self):
        self.engine.process_action("get_exposure_history", {})
        result = self.engine.process_action("calculate_attack_rate", {"food_item": "nonexistent_food_xyz"})
        assert result["result_type"] == "attack_rate"
        assert not result["data"]

    def test_attack_rate_valid_food(self):
        self.engine.process_action("get_exposure_history", {})
        food = self.scenario.menu_items[0]
        result = self.engine.process_action("calculate_attack_rate", {"food_item": food})
        assert result["result_type"] == "attack_rate"
        assert "relative_risk" in result["data"]

    def test_hypothesis_cap(self):
        for _ in range(3):
            r = self.engine.process_action("submit_hypothesis", {"pathogen": "x", "source": "y", "route": "z"})
            assert r["result_type"] == "hypothesis_feedback"
        # 4th attempt should fail
        r = self.engine.process_action("submit_hypothesis", {"pathogen": "x", "source": "y", "route": "z"})
        assert r["result_type"] == "error"

    def test_hypothesis_per_component_feedback(self):
        gt = self.scenario.ground_truth
        r = self.engine.process_action("submit_hypothesis", {
            "pathogen": gt["pathogen"],
            "source": "wrong_source",
            "route": gt["route"],
        })
        assert r["result_type"] == "hypothesis_feedback"
        assert r["data"]["pathogen_correct"] is True
        assert r["data"]["source_correct"] is False
        assert r["data"]["route_correct"] is True

    def test_line_list_returns_cases(self):
        result = self.engine.process_action("request_line_list", {})
        assert result["result_type"] == "line_list"
        assert len(result["data"]["cases"]) > 0

    def test_lab_results_contain_positives(self):
        result = self.engine.process_action("request_lab_results", {})
        assert result["result_type"] == "lab_results"
        assert any(r["result"] == "POSITIVE" for r in result["data"]["results"].values())
