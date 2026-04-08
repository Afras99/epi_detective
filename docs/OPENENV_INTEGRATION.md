# OpenEnv Integration Spec

## Overview

EpiDetective follows the OpenEnv spec exactly: FastAPI server in Docker, WebSocket-based client, typed Pydantic models for Action/Observation, and the standard `step()`/`reset()`/`state()` API.

---

## models.py

```python
from pydantic import Field
from openenv.core.env_server.types import Action, Observation
from typing import Optional

class EpiAction(Action):
    """Agent's investigation action."""
    command: str = Field(
        ...,
        description=(
            "One of: view_initial_alert, request_line_list, "
            "generate_epi_curve, request_lab_results, "
            "get_exposure_history, calculate_attack_rate, "
            "calculate_odds_ratio, request_environmental_samples, "
            "submit_hypothesis, submit_final_answer"
        )
    )
    parameters: dict = Field(
        default_factory=dict,
        description=(
            "Command-specific parameters. Examples: "
            "{'grouping': 'hour'} for epi curve, "
            "{'case_ids': ['c001','c002']} for lab results, "
            "{'food_item': 'potato_salad'} for attack rate, "
            "{'pathogen': 'salmonella', 'source': 'eggs', 'route': 'foodborne'} for submission"
        )
    )

class EpiObservation(Observation):
    """What the agent sees after each action."""
    result_type: str = Field(
        ..., description="Type: alert, line_list, epi_curve, lab_results, "
                         "exposure_history, attack_rate, odds_ratio, "
                         "environmental, hypothesis_feedback, final_score, error"
    )
    data: dict = Field(
        default_factory=dict,
        description="Structured evidence data"
    )
    narrative: str = Field(
        ..., description="Natural language description of findings"
    )
    hint: Optional[str] = Field(
        None, description="Subtle hint (Task 1 only)"
    )
    available_actions: list[str] = Field(
        default_factory=list,
        description="Valid actions the agent can take next"
    )
    step_reward: float = Field(
        0.0, description="Immediate reward signal for this step"
    )
```

---

## server/epi_environment.py

```python
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State, StepResult
from models import EpiAction, EpiObservation
from engine.scenario_generator import ScenarioGenerator
from engine.evidence_engine import EvidenceEngine
from grader.grader import EpiGrader
from grader.reward import compute_step_reward
import random

class EpiDetectiveEnvironment(Environment):
    """Disease outbreak investigation environment."""
    
    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._scenario = None
        self._evidence_engine = None
        self._grader = EpiGrader()
        self._generator = ScenarioGenerator()
        self._action_history = set()
        self._done = False
    
    def reset(self, task_id: str = "easy", seed: int = None) -> StepResult:
        """
        Reset environment with a new scenario.
        
        Args:
            task_id: "easy", "medium", or "hard"
            seed: Random seed for reproducibility (optional)
        """
        if seed is None:
            seed = random.randint(0, 2**32 - 1)
        
        self._state = State(
            episode_id=str(uuid4()),
            step_count=0,
            metadata={"task_id": task_id, "seed": seed}
        )
        self._scenario = self._generator.generate(task_id, seed)
        self._evidence_engine = EvidenceEngine(self._scenario)
        self._action_history = set()
        self._done = False
        
        # Return the initial alert
        initial_obs = EpiObservation(
            result_type="alert",
            data={"task_id": task_id, "setting": self._scenario.setting},
            narrative=self._scenario.initial_alert,
            available_actions=self._get_available_actions(),
            step_reward=0.0
        )
        
        return StepResult(
            observation=initial_obs,
            reward=0.0,
            done=False,
            state=self._state
        )
    
    def step(self, action: EpiAction) -> StepResult:
        """Process one investigation action."""
        if self._done:
            return StepResult(
                observation=EpiObservation(
                    result_type="error",
                    data={},
                    narrative="Investigation is complete. Call reset() to start a new case.",
                    available_actions=[],
                    step_reward=0.0
                ),
                reward=0.0,
                done=True,
                state=self._state
            )
        
        self._state.step_count += 1
        
        # Check if this is a final submission
        is_final = action.command == "submit_final_answer"
        
        # Process the action through evidence engine
        observation = self._evidence_engine.process_action(action)
        
        # Compute step reward
        reward = compute_step_reward(
            action, self._action_history,
            self._scenario.ground_truth,
            self._state.step_count,
            self._scenario.optimal_steps,
            self._scenario.max_steps
        )
        
        # Track action history
        action_key = f"{action.command}:{str(sorted(action.parameters.items()))}"
        self._action_history.add(action_key)
        
        # If final submission, grade it
        if is_final:
            final_score = self._grader.grade(
                action.parameters,
                self._scenario.ground_truth,
                self._scenario
            )
            reward = final_score
            self._done = True
            observation.narrative += f"\n\nFinal score: {final_score:.4f}"
            observation.step_reward = final_score
        else:
            observation.step_reward = reward
        
        # Check step budget
        if self._state.step_count >= self._scenario.max_steps and not is_final:
            self._done = True
            observation.narrative += "\n\nStep budget exhausted. Submit your final answer."
            observation.available_actions = ["submit_final_answer"]
        
        return StepResult(
            observation=observation,
            reward=reward,
            done=self._done,
            state=self._state
        )
    
    def state(self) -> State:
        """Return current environment state."""
        return State(
            episode_id=self._state.episode_id,
            step_count=self._state.step_count,
            metadata={
                "task_id": self._state.metadata.get("task_id"),
                "actions_taken": list(self._action_history),
                "evidence_unlocked": list(self._evidence_engine.unlocked) if self._evidence_engine else [],
                "done": self._done,
                "steps_remaining": (self._scenario.max_steps - self._state.step_count) if self._scenario else 0
            }
        )
    
    def _get_available_actions(self):
        return [
            "view_initial_alert",
            "request_line_list",
            "generate_epi_curve",
            "request_lab_results",
            "get_exposure_history",
            "calculate_attack_rate",
            "calculate_odds_ratio",
            "request_environmental_samples",
            "submit_hypothesis",
            "submit_final_answer"
        ]
```

---

## openenv.yaml

```yaml
name: epi_detective
version: "0.1.0"
description: "Disease outbreak investigation environment for training AI epidemiologist agents"
author: "Afras Aboobacker P"
license: "MIT"

environment:
  class: "server.epi_environment.EpiDetectiveEnvironment"
  action_type: "models.EpiAction"
  observation_type: "models.EpiObservation"

tasks:
  - id: "easy"
    name: "Point-source foodborne outbreak"
    description: "Investigate a single-source foodborne outbreak at a shared meal event"
    difficulty: "easy"
    max_steps: 15
  - id: "medium"
    name: "Community respiratory outbreak"
    description: "Investigate a Legionella outbreak amid concurrent influenza season"
    difficulty: "medium"
    max_steps: 25
  - id: "hard"
    name: "Multi-source overlapping outbreaks"
    description: "Separate and investigate two simultaneous outbreaks in a metro area"
    difficulty: "hard"
    max_steps: 35

deployment:
  runtime: "docker"
  port: 7860
  resources:
    vcpu: 2
    memory_gb: 8
```

---

## server/Dockerfile

```dockerfile
ARG BASE_IMAGE=openenv-base:latest
FROM ${BASE_IMAGE} AS builder
WORKDIR /app

ARG BUILD_MODE=in-repo
ARG ENV_NAME=epi_detective

# Copy environment code
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir \
    faker>=28.0.0 \
    numpy>=1.24.0 \
    && pip install --no-cache-dir -e .

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

## server/requirements.txt

```
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
faker>=28.0.0
numpy>=1.24.0
openenv-core>=0.2.0
```

---

## pyproject.toml

```toml
[project]
name = "epi-detective"
version = "0.1.0"
description = "Disease outbreak investigation OpenEnv environment"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "Afras Aboobacker P"}]

dependencies = [
    "openenv-core>=0.2.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    "faker>=28.0.0",
    "numpy>=1.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "httpx>=0.24.0",
]
```

---

## inference.py (LLM agent)

```python
"""
EpiDetective LLM Agent
Uses OpenAI Client for all LLM calls per hackathon requirements.
Implements ReAct-style: Observe → Think → Act loop.
"""
import os
import json
import re
from openai import OpenAI

# Required env vars (set by hackathon platform)
API_BASE_URL = os.environ["API_BASE_URL"]
MODEL_NAME = os.environ["MODEL_NAME"]
HF_TOKEN = os.environ.get("HF_TOKEN", "")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "dummy")

SYSTEM_PROMPT = """You are an expert epidemiologist investigating a disease outbreak.

## Available investigation tools (use ONE per turn):
- view_initial_alert() — Read the outbreak notification
- request_line_list() — Get patient demographics, onset dates, symptoms
- generate_epi_curve(grouping="hour"|"day") — Temporal case distribution
- request_lab_results(case_ids=["c001","c002"]) — Pathogen lab results for specific cases
- get_exposure_history(case_ids=["c001","c002"]) — What patients ate/visited
- calculate_attack_rate(food_item="potato_salad") — Ate-ill vs ate-well statistical comparison
- calculate_odds_ratio(exposure="restaurant_x") — Statistical association measure
- request_environmental_samples(location="kitchen") — Environmental lab tests
- submit_hypothesis(pathogen="...", source="...", route="...") — Test theory (get partial feedback)
- submit_final_answer(pathogen="...", source="...", route="...", case_definition={...}) — Final submission

## Respond in this EXACT format:
THOUGHT: [Your reasoning about what evidence to gather next]
ACTION: {"command": "request_line_list", "parameters": {}}

## Investigation strategy:
1. Read the alert → understand the scope and setting
2. Request line list → see demographics, onset dates, symptoms
3. Generate epi curve → estimate incubation period (narrows pathogen type)
4. Request lab results → identify the pathogen
5. Get exposure histories → see what people ate/visited
6. Calculate attack rates for suspicious foods → find the source
7. Submit final answer with pathogen, source, route, and case definition

Be efficient — each step costs points. Don't repeat queries."""

def parse_action(response_text):
    """Extract action JSON from LLM response."""
    # Look for ACTION: {...} pattern
    match = re.search(r'ACTION:\s*(\{.*?\})', response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Fallback: try to find any JSON object
    match = re.search(r'\{[^{}]*"command"[^{}]*\}', response_text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Default: request line list (safe first action)
    return {"command": "request_line_list", "parameters": {}}

def run_agent(env_client, task_id="easy"):
    """Run the LLM agent through a full investigation."""
    # Reset environment
    result = env_client.reset(task_id=task_id)
    
    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"New outbreak alert:\n\n{result.observation.narrative}\n\nBegin your investigation."}
    ]
    
    total_reward = 0.0
    max_turns = 20  # Safety limit
    
    for turn in range(max_turns):
        # Get LLM response
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=conversation,
            max_tokens=800,
            temperature=0.3  # Low temperature for systematic reasoning
        )
        
        assistant_msg = response.choices[0].message.content
        conversation.append({"role": "assistant", "content": assistant_msg})
        
        # Parse action
        action_dict = parse_action(assistant_msg)
        
        # Execute in environment
        from models import EpiAction
        action = EpiAction(**action_dict)
        step_result = env_client.step(action)
        
        total_reward += step_result.reward
        
        # Build observation message for LLM
        obs_msg = (
            f"OBSERVATION:\n{step_result.observation.narrative}\n\n"
            f"Step reward: {step_result.observation.step_reward:.4f}\n"
            f"Steps remaining: {step_result.state.metadata.get('steps_remaining', '?')}\n"
            f"Available actions: {', '.join(step_result.observation.available_actions)}"
        )
        conversation.append({"role": "user", "content": obs_msg})
        
        if step_result.done:
            print(f"Investigation complete. Final score: {step_result.reward:.4f}")
            break
    
    return total_reward

if __name__ == "__main__":
    from client import EpiDetectiveEnv
    
    # Connect to the running environment
    env_url = os.environ.get("ENV_URL", "http://localhost:7860")
    
    with EpiDetectiveEnv(base_url=env_url).sync() as env:
        for task in ["easy", "medium", "hard"]:
            print(f"\n{'='*50}")
            print(f"Running Task: {task}")
            print(f"{'='*50}")
            score = run_agent(env, task_id=task)
            print(f"Task {task} score: {score:.4f}")
```

---

## client.py

```python
from openenv.core.env_client import HTTPEnvClient
from models import EpiAction, EpiObservation

class EpiDetectiveEnv(HTTPEnvClient[EpiAction, EpiObservation]):
    """Typed client for the EpiDetective environment."""
    
    env_id = "epi_detective"
    action_type = EpiAction
    observation_type = EpiObservation
```
