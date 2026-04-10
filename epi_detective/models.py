"""
EpiDetective models — extends OpenEnv core types.

These are the typed contracts shared by server, client, and inference script.
They MUST extend openenv.core.env_server.types.Action and Observation
so that create_app() can serialize/deserialize them over WebSocket.
"""
from typing import Any, Dict, List, Optional
from pydantic import Field

from openenv.core.env_server.types import Action, Observation


class EpiAction(Action):
    """Agent's investigation action — sent via WebSocket or POST /step."""
    command: str = Field(
        default="request_line_list",
        description=(
            "Investigation command. One of: view_initial_alert, request_line_list, "
            "generate_epi_curve, request_lab_results, get_exposure_history, "
            "calculate_attack_rate, calculate_odds_ratio, request_environmental_samples, "
            "submit_hypothesis, submit_final_answer"
        ),
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Command-specific parameters (e.g. {'food_item': 'chicken'})",
    )


class EpiObservation(Observation):
    """What the agent observes after each action."""
    result_type: str = Field(default="", description="Type of result returned")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured evidence data")
    narrative: str = Field(default="", description="Human-readable description of findings")
    available_actions: List[str] = Field(default_factory=list, description="Valid next actions")
    step_reward: float = Field(default=0.0, description="Reward for this step")