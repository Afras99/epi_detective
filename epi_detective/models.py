# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Canonical Pydantic models for EpiDetective — shared by server, client, and inference script.

EpiAction — what the agent sends to POST /step:
    command      — one of 10 investigation commands (view_initial_alert, request_line_list,
                   generate_epi_curve, request_lab_results, get_exposure_history,
                   calculate_attack_rate, calculate_odds_ratio, request_environmental_samples,
                   submit_hypothesis, submit_final_answer)
    parameters   — command-specific dict (e.g. {"food_item": "chicken"})
    session_id   — optional session identifier for concurrent use (default session if omitted)

EpiObservation — what the agent receives back from POST /step and POST /reset:
    result_type  — line_list | lab_results | attack_rate | odds_ratio | epi_curve |
                   exposure_history | environmental | hypothesis_feedback | final_score | error | alert
    data         — structured result (patient records, 2×2 tables, lab findings, etc.)
    narrative    — plain-English summary an LLM agent reads directly
    available_actions — commands the agent may call next
    step_reward  — reward this step: +0.02–0.08 for new evidence, -0.02 for repeats, 0 for hypothesis
    done         — True after submit_final_answer
    reward       — final grader score (0.001–0.999) when done=True, else step_reward
    metadata     — extra debug info

Imported by server/app.py (ActionRequest extends EpiAction, StepResponse extends EpiObservation),
and available to inference.py and client.py for typed interactions.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EpiAction(BaseModel):
    """Agent's investigation action — sent to POST /step."""
    command: str = Field(
        default="request_line_list",
        description="Investigation command. One of: view_initial_alert, request_line_list, "
                    "generate_epi_curve, request_lab_results, get_exposure_history, "
                    "calculate_attack_rate, calculate_odds_ratio, request_environmental_samples, "
                    "submit_hypothesis, submit_final_answer",
    )
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command-specific parameters")
    session_id: Optional[str] = Field(default=None, description="Session identifier (uses default session if omitted)")


class EpiObservation(BaseModel):
    """What the agent observes after each action — base class for StepResponse."""
    result_type: str = Field(default="", description="Result type tag")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured result data")
    narrative: str = Field(default="", description="Human-readable finding narrative")
    available_actions: List[str] = Field(default_factory=list, description="Commands available next")
    step_reward: float = Field(default=0.0, description="Reward earned this step")
    done: bool = Field(default=False, description="True when submit_final_answer has been called")
    reward: float = Field(default=0.0, description="Final grader score (0.001–0.999) when done, else step_reward")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra debug metadata")
