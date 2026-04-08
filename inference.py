"""
EpiDetective Inference Script
==============================
Baseline ReAct-style agent for the EpiDetective environment.
Uses the OpenAI Client as required by the hackathon spec.

Environment variables:
    API_BASE_URL  — LLM API endpoint (default: https://router.huggingface.co/v1)
    MODEL_NAME    — Model identifier (default: meta-llama/Llama-3.1-8B-Instruct)
    HF_TOKEN      — Hugging Face / API key
    ENV_URL       — Environment server URL (default: http://localhost:7860)

STDOUT FORMAT (mandatory):
    [START] task=<task_name> env=epi_detective model=<model_name>
    [STEP]  step=<n> action=<command> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>
"""

import json
import os
import re
import time
from typing import List, Optional

import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", "")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
BENCHMARK = "epi_detective"
SUCCESS_SCORE_THRESHOLD = 0.3

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "dummy")

SYSTEM_PROMPT = """You are an expert epidemiologist investigating a disease outbreak.

## Available tools (use ONE per turn):
- view_initial_alert — Read the outbreak notification
- request_line_list — Get patient demographics, onset dates, symptoms
- generate_epi_curve — Temporal case distribution (params: {"grouping": "hour"})
- request_lab_results — Pathogen lab results (params: {"case_ids": ["c001","c002"]})
- get_exposure_history — What patients ate/visited (params: {"case_ids": ["c001"]})
- calculate_attack_rate — Statistical food analysis (params: {"food_item": "potato_salad"})
- calculate_odds_ratio — Association measure (params: {"exposure": "chicken"})
- request_environmental_samples — Facility tests (params: {"location": "kitchen"})
- submit_hypothesis — Test theory (params: {"pathogen": "...", "source": "...", "route": "..."})
- submit_final_answer — Final submission (params: {"pathogen": "...", "source": "...", "route": "...", "case_definition": {"clinical": "...", "time": "...", "place": "..."}})

## Response format — ALWAYS use this exact format:
THOUGHT: [your reasoning about the evidence so far]
ACTION: {"command": "request_line_list", "parameters": {}}

## Investigation strategy:
1. request_line_list — see who got sick and when (incubation period clues)
2. request_lab_results — identify the pathogen from specimens
3. get_exposure_history — see what patients ate at the event
4. calculate_attack_rate — find the highest-risk food statistically
5. submit_final_answer — report pathogen, source, route, case definition

Be systematic. Avoid repeating actions (costs -0.02 each)."""

AVAILABLE_ACTIONS = [
    "view_initial_alert", "request_line_list", "generate_epi_curve",
    "request_lab_results", "get_exposure_history", "calculate_attack_rate",
    "calculate_odds_ratio", "request_environmental_samples",
    "submit_hypothesis", "submit_final_answer",
]

TASK_MAX_TURNS = {"easy": 15, "medium": 25, "hard": 35}


# ── Structured log helpers (mandatory format) ─────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Sanitise action: strip newlines so log stays single-line
    action_clean = action.replace("\n", " ").replace("\r", "")[:120]
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# ── Environment helpers ───────────────────────────────────────────────────────

def wait_for_server(timeout: int = 120) -> None:
    """Poll /health until the server is ready."""
    print(f"[DEBUG] Waiting for server at {ENV_URL} ...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{ENV_URL}/health", timeout=5)
            if r.status_code == 200:
                print(f"[DEBUG] Server ready.", flush=True)
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError(f"Server at {ENV_URL} did not become ready within {timeout}s")


def env_reset(task_id: str) -> dict:
    resp = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def env_step(command: str, parameters: dict) -> dict:
    resp = requests.post(
        f"{ENV_URL}/step",
        json={"command": command, "parameters": parameters},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── LLM helpers ───────────────────────────────────────────────────────────────

def parse_action(text: str) -> dict:
    """Extract the ACTION JSON from LLM response text."""
    match = re.search(r'ACTION:\s*(\{.*?\})', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r'\{[^{}]*"command"[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    text_lower = text.lower()
    for action in AVAILABLE_ACTIONS:
        if action.replace("_", " ") in text_lower or action in text_lower:
            return {"command": action, "parameters": {}}

    return {"command": "request_line_list", "parameters": {}}


def get_llm_action(messages: list) -> str:
    """Call the LLM and return the raw response text."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=800,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"[DEBUG] LLM error: {e}", flush=True)
        return (
            'ACTION: {"command": "submit_final_answer", "parameters": {'
            '"pathogen": "unknown", "source": "unknown", "route": "foodborne",'
            '"case_definition": {"clinical": "gastrointestinal illness", "time": "unknown", "place": "unknown"}}}'
        )


# ── Main task runner ──────────────────────────────────────────────────────────

def run_task(task_id: str) -> float:
    max_turns = TASK_MAX_TURNS.get(task_id, 15)
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    episode_done = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = env_reset(task_id)
        alert = result["observation"]["narrative"]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"New outbreak investigation:\n\n{alert}\n\n"
                "Begin your investigation. Use the ACTION format."
            )},
        ]

        for turn in range(1, max_turns + 1):
            assistant_msg = get_llm_action(messages)
            messages.append({"role": "assistant", "content": assistant_msg})

            action = parse_action(assistant_msg)
            command = action["command"]
            parameters = action.get("parameters", {})

            error_msg = None
            try:
                result = env_step(command, parameters)
                obs = result["observation"]
                reward = float(result["reward"])
                done = bool(result["done"])
            except Exception as e:
                error_msg = str(e)[:100]
                reward = 0.0
                done = False
                rewards.append(reward)
                steps_taken = turn
                log_step(step=turn, action=command, reward=reward, done=done, error=error_msg)
                break

            rewards.append(reward)
            steps_taken = turn

            log_step(step=turn, action=command, reward=reward, done=done, error=error_msg)

            if done:
                score = reward
                success = score >= SUCCESS_SCORE_THRESHOLD
                episode_done = True
                break

            obs_text = (
                f"OBSERVATION:\n{obs.get('narrative', '')}\n\n"
                f"Step reward: {obs.get('step_reward', 0):.4f}\n"
                f"Steps remaining: {result['state'].get('steps_remaining', '?')}\n"
                f"Available actions: {', '.join(obs.get('available_actions', []))}"
            )
            messages.append({"role": "user", "content": obs_text})

        # Force submit if episode never ended naturally
        if not episode_done:
            turn = steps_taken + 1
            error_msg = None
            try:
                result = env_step("submit_final_answer", {
                    "pathogen": "unknown", "source": "unknown", "route": "foodborne",
                    "case_definition": {
                        "clinical": "gastrointestinal illness",
                        "time": "unknown onset",
                        "place": "unknown location",
                    },
                })
                reward = float(result["reward"])
                score = reward
                done = True
            except Exception as e:
                error_msg = str(e)[:100]
                reward = 0.0
                score = 0.0
                done = True
                episode_done = True

            rewards.append(reward)
            steps_taken = turn
            success = score >= SUCCESS_SCORE_THRESHOLD
            log_step(step=turn, action="submit_final_answer", reward=reward, done=done, error=error_msg)

    except Exception as e:
        print(f"[DEBUG] Task {task_id} exception: {e}", flush=True)
        score = 0.0
        success = False

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    wait_for_server()

    all_scores = {}
    for task in ["easy", "medium", "hard"]:
        try:
            all_scores[task] = run_task(task)
        except Exception as e:
            print(f"[DEBUG] Task {task} failed: {e}", flush=True)
            # Still emit [END] so validator doesn't hang
            log_end(success=False, steps=0, score=0.0, rewards=[])
            all_scores[task] = 0.0

    print(f"\n[DEBUG] FINAL SCORES: easy={all_scores.get('easy',0):.3f} "
          f"medium={all_scores.get('medium',0):.3f} "
          f"hard={all_scores.get('hard',0):.3f}", flush=True)
