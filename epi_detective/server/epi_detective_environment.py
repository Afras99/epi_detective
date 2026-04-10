"""
EpiDetective Environment — extends openenv.core.env_server.interfaces.Environment.

This is the core environment class that the OpenEnv framework wraps with
WebSocket endpoints, health checks, and the Gradio web UI via create_app().

All outbreak logic is delegated to:
  - engine/scenario_generator.py  → builds scenarios
  - engine/evidence_engine.py     → gates evidence behind actions
  - grader/grader.py              → deterministic scoring
"""
import json
import random
import sys
from pathlib import Path
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

# Ensure engine/ and grader/ are importable
_pkg_root = Path(__file__).parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from engine.scenario_generator import ScenarioGenerator
from engine.evidence_engine import EvidenceEngine
from grader.grader import EpiGrader, compute_step_reward
from models import EpiAction, EpiObservation

AVAILABLE_ACTIONS = [
    "view_initial_alert",
    "request_line_list",
    "generate_epi_curve",
    "request_lab_results",
    "get_exposure_history",
    "calculate_attack_rate",
    "calculate_odds_ratio",
    "request_environmental_samples",
    "submit_hypothesis",
    "submit_final_answer",
]


class EpiDetectiveEnvironment(Environment):
    """
    Disease outbreak investigation environment.

    The agent plays a field epidemiologist who must identify the pathogen,
    food source, and transmission route of a disease outbreak by
    strategically gathering evidence.

    Three difficulty levels:
      easy   — single-source foodborne outbreak (15 steps)
      medium — community outbreak with noise (25 steps)
      hard   — two overlapping outbreaks (35 steps)
    """

    def __init__(self):
        super().__init__()
        self._generator = ScenarioGenerator()
        self._grader = EpiGrader()
        self._scenario = None
        self._evidence_engine = None
        self._action_history: set = set()
        self._step_count = 0
        self._total_reward = 0.0
        self._is_done = False
        self._task_id = "easy"
        self._state = State(episode_id=str(uuid4()), step_count=0)

    def reset(self, seed: int = None, **kwargs) -> EpiObservation:
        """Start a new outbreak investigation."""
        self._task_id = kwargs.get("task_id", "easy")
        if seed is None:
            seed = random.randint(0, 2**31)

        self._scenario = self._generator.generate(self._task_id, seed)
        self._evidence_engine = EvidenceEngine(self._scenario)
        self._action_history = set()
        self._step_count = 0
        self._total_reward = 0.0
        self._is_done = False
        self._state = State(episode_id=str(uuid4()), step_count=0)

        return EpiObservation(
            result_type="alert",
            data={"task_id": self._task_id, "seed": seed},
            narrative=self._scenario.initial_alert,
            available_actions=AVAILABLE_ACTIONS,
            step_reward=0.0,
            done=False,
            reward=0.0,
        )

    def step(self, action: EpiAction, **kwargs) -> EpiObservation:
        """Execute one investigation action."""
        if self._is_done:
            return EpiObservation(
                result_type="error",
                narrative="Investigation complete. Call reset() to start a new case.",
                data={},
                available_actions=[],
                done=True,
                reward=0.0,
            )

        if self._scenario is None:
            return EpiObservation(
                result_type="error",
                narrative="No active investigation. Call reset() first.",
                data={},
                available_actions=[],
                done=False,
                reward=0.0,
            )

        self._step_count += 1
        self._state = State(
            episode_id=self._state.episode_id,
            step_count=self._step_count,
        )
        command = action.command
        params = action.parameters

        # ── Final submission ──
        if command == "submit_final_answer":
            final_score = self._grader.grade(
                params,
                self._scenario.ground_truth,
                self._step_count,
                self._scenario.optimal_steps,
                self._scenario.max_steps,
            )
            self._is_done = True
            self._total_reward = final_score

            return EpiObservation(
                result_type="final_score",
                data={"score": final_score, "steps_taken": self._step_count},
                narrative=f"Investigation complete. Final score: {final_score:.4f} / 1.0 ({self._step_count} steps taken).",
                available_actions=[],
                step_reward=final_score,
                done=True,
                reward=final_score,
            )

        # ── Regular investigation actions ──
        obs_data = self._evidence_engine.process_action(command, params)

        step_reward = compute_step_reward(
            command, params, self._action_history,
            self._scenario.ground_truth,
        )
        action_key = f"{command}:{json.dumps(params, sort_keys=True)}"
        self._action_history.add(action_key)
        self._total_reward += step_reward

        # Check step budget
        remaining = self._scenario.max_steps - self._step_count
        if remaining <= 0:
            available = ["submit_final_answer"]
            obs_data["narrative"] += "\n\n⚠️ Step budget exhausted! You must submit your final answer now."
        else:
            available = AVAILABLE_ACTIONS

        return EpiObservation(
            result_type=obs_data.get("result_type", "evidence"),
            data=obs_data.get("data", {}),
            narrative=obs_data.get("narrative", ""),
            available_actions=available,
            step_reward=step_reward,
            done=False,
            reward=step_reward,
        )

    @property
    def state(self) -> State:
        """Return current episode state."""
        return self._state