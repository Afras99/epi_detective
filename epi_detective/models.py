# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Pydantic models for the Epi Detective environment.

Agents submit investigation commands; the environment returns rich observations
with narrative text, structured data, and per-step rewards.
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
