# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
EpiDetective HTTP Client.

Thin HTTP wrapper around the EpiDetective server REST API.

Example:
    >>> client = EpiDetectiveClient("http://localhost:7860")
    >>> obs = client.reset(task_id="easy")
    >>> print(obs["observation"]["narrative"])
    >>>
    >>> result = client.step("request_line_list")
    >>> result = client.step("calculate_attack_rate", {"food_item": "potato_salad"})
    >>> result = client.step("submit_final_answer", {
    ...     "pathogen": "salmonella",
    ...     "source": "potato_salad",
    ...     "route": "foodborne",
    ...     "case_definition": {"clinical": "diarrhea", "time": "6h after meal", "place": "potluck"},
    ... })
    >>> print(result["reward"])
"""

from typing import Any, Dict, Optional

import requests


class EpiDetectiveClient:
    """HTTP client for the EpiDetective environment server."""

    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()

    def reset(self, task_id: str = "easy", seed: Optional[int] = None) -> Dict[str, Any]:
        """Reset the environment and start a new investigation.

        Args:
            task_id: Difficulty level — "easy", "medium", or "hard"
            seed: Optional random seed for reproducibility

        Returns:
            StepResponse dict with observation, reward, done, state
        """
        payload: Dict[str, Any] = {"task_id": task_id}
        if seed is not None:
            payload["seed"] = seed
        resp = self._session.post(f"{self.base_url}/reset", json=payload)
        resp.raise_for_status()
        return resp.json()

    def step(self, command: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute one investigation action.

        Args:
            command: Investigation command (e.g. "request_line_list")
            parameters: Optional command parameters

        Returns:
            StepResponse dict with observation, reward, done, state
        """
        resp = self._session.post(
            f"{self.base_url}/step",
            json={"command": command, "parameters": parameters or {}},
        )
        resp.raise_for_status()
        return resp.json()

    def state(self) -> Dict[str, Any]:
        """Get current environment state."""
        resp = self._session.get(f"{self.base_url}/state")
        resp.raise_for_status()
        return resp.json()

    def health(self) -> Dict[str, Any]:
        """Check server health."""
        resp = self._session.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def schema(self) -> Dict[str, Any]:
        """Get action/observation schema."""
        resp = self._session.get(f"{self.base_url}/schema")
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

