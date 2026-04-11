"""
EpiDetective Client — extends OpenEnv's EnvClient for typed WebSocket interaction.

Usage:
    # Async (recommended)
    async with EpiDetectiveEnv(base_url="ws://localhost:7860") as env:
        result = await env.reset(task_id="easy")
        result = await env.step(EpiAction(command="request_line_list"))

    # Sync wrapper
    with EpiDetectiveEnv(base_url="ws://localhost:7860").sync() as env:
        result = env.reset(task_id="easy")
        result = env.step(EpiAction(command="request_line_list"))

    # From Docker
    client = await EpiDetectiveEnv.from_docker_image("epi-detective:latest")

    # From HF Space
    client = await EpiDetectiveEnv.from_env("username/epi-detective")
"""
import sys
from pathlib import Path

_pkg_root = Path(__file__).parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State
try:
    from epi_detective.models import EpiAction, EpiObservation
except ImportError:
    from models import EpiAction, EpiObservation  # type: ignore


class EpiDetectiveEnv(EnvClient[EpiAction, EpiObservation, State]):
    """Typed WebSocket client for EpiDetective."""

    def _step_payload(self, action: EpiAction) -> dict:
        """Serialize action for the wire."""
        return {
            "command": action.command,
            "parameters": action.parameters,
        }

    def _parse_result(self, payload: dict) -> StepResult[EpiObservation]:
        """Deserialize server response into typed StepResult."""
        obs_data = payload.get("observation", {})
        obs = EpiObservation(
            result_type=obs_data.get("result_type", ""),
            data=obs_data.get("data", {}),
            narrative=obs_data.get("narrative", ""),
            available_actions=obs_data.get("available_actions", []),
            step_reward=obs_data.get("step_reward", 0.0),
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
        )
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> State:
        """Deserialize state response."""
        return State(
            episode_id=payload.get("episode_id", ""),
            step_count=payload.get("step_count", 0),
        )