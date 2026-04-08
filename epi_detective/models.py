# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Pydantic models for EpiDetective.

EpiAction — what the agent sends to POST /step:
    command     — one of 10 investigation commands (see README for full list)
    parameters  — command-specific dict (e.g. {"food_item": "chicken"})

EpiObservation — what the agent receives back:
    result_type  — type tag: line_list | lab_results | attack_rate | final_score | error | ...
    data         — structured result (patient records, 2×2 tables, lab findings, etc.)
    narrative    — plain-English summary an LLM agent can read directly
    available_actions — commands the agent may call next
    step_reward  — reward earned this step (+0.02 to +0.08, or -0.02 for repeats)
    done         — True when submit_final_answer has been called
    reward       — final score (0.0–1.0) on done=True, else same as step_reward
    metadata     — extra debug info

Used by inference.py for typed agent interactions and by client.py for the WebSocket client.
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class EpiAction(BaseModel):
    """Agent's investigation action."""
    command: str = Field(default="", description="Investigation command to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")


class EpiObservation(BaseModel):
    """What the agent sees after each action."""
    result_type: str = Field(default="", description="Type of result returned")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured result data")
    narrative: str = Field(default="", description="Human-readable description of findings")
    available_actions: List[str] = Field(default_factory=list, description="Commands available next")
    step_reward: float = Field(default=0.0, description="Reward for this step")
    done: bool = Field(default=False, description="Whether the episode is complete")
    reward: float = Field(default=0.0, description="Cumulative or final reward")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")
