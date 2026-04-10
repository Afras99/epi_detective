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
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
BENCHMARK = "epi_detective"
SUCCESS_SCORE_THRESHOLD = 0.3

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

SYSTEM_PROMPT = """You are an expert CDC field epidemiologist investigating a disease outbreak.

## Available tools (use ONE per turn):
- view_initial_alert — Read the outbreak notification
- request_line_list — Get patient demographics, onset dates, symptoms
- generate_epi_curve — Temporal case distribution (params: {"grouping": "hour"})
- request_lab_results — Pathogen lab results (params: {} for first 10 cases)
- get_exposure_history — What patients ate (params: {} for first 15 ill patients)
- calculate_attack_rate — 2x2 table + relative risk (params: {"food_item": "<exact_food_name_from_exposure_history>"})
- calculate_odds_ratio — Odds ratio (params: {"exposure": "<exact_food_name_from_exposure_history>"})
- request_environmental_samples — Facility swabs (params: {"location": "kitchen"})
- submit_hypothesis — Test theory, get per-component feedback (params: {"pathogen": "...", "source": "...", "route": "..."})
- submit_final_answer — End episode with full answer (params below)

## Response format — ALWAYS use this exact format:
THOUGHT: [your reasoning about the evidence so far]
ACTION: {"command": "<command_name>", "parameters": {<params>}}

## Optimal investigation strategy:
1. request_line_list — check incubation: short <6h = toxin (S.aureus/B.cereus), 6-24h = bacterial toxin, 24-72h = Salmonella/E.coli, >72h = parasites/Hep A
2. generate_epi_curve — note onset span and date window; narrow peak = point-source exposure
3. request_lab_results — confirm pathogen from organism names in results
4. get_exposure_history — read the EXACT food names listed (use these verbatim in attack rate calls)
5. calculate_attack_rate for the TOP 3 foods by case exposure count — pick food with highest relative risk (>2.0 implicates it)
6. submit_hypothesis — check pathogen/source/route before final submission
7. submit_final_answer — with full case definition

## submit_final_answer parameters:
{
  "pathogen": "<organism from lab results>",
  "source": "<food with highest relative risk, exact name from exposure history>",
  "route": "foodborne",
  "case_definition": {
    "clinical": "<specific symptoms listed in line list> confirmed by <lab method>",
    "time": "<onset window from epi curve, e.g. 12-48 hours after the meal on [date]>",
    "place": "<specific event and venue from the initial alert>"
  }
}

## Rules:
- NEVER repeat the same action with same parameters (costs -0.02)
- Food names in parameters must EXACTLY match exposure history output (underscores, no spaces)
- Route values: foodborne / waterborne / person_to_person / environmental_airborne / animal_contact
"""

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


def log_step(
    step: int, action: str, reward: float, done: bool, error: Optional[str]
) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    action_clean = action.replace("\n", " ").replace("\r", "")[:120]
    print(
        f"[STEP] step={step} action={action_clean} "
        f"reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(
    success: bool, steps: int, score: float, rewards: List[float]
) -> None:
    score = max(0.001, min(0.999, score))
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── Environment helpers ───────────────────────────────────────────────────────

def wait_for_server(timeout: int = 120) -> None:
    """Poll /health until the server is ready."""
    print(f"[DEBUG] Waiting for server at {ENV_URL} ...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{ENV_URL}/health", timeout=5)
            if r.status_code == 200:
                print("[DEBUG] Server ready.", flush=True)
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError(
        f"Server at {ENV_URL} did not become ready within {timeout}s"
    )


def env_reset(task_id: str) -> dict:
    resp = requests.post(
        f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30
    )
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
    match = re.search(r'ACTION:\s*(\{[^{}]*\})', text)
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
        return ""


def get_llm_final_answer(messages: list) -> dict:
    """Ask the LLM to synthesize collected evidence into a final answer."""
    synthesis_prompt = (
        "You have reached the step limit. Based on ALL the evidence collected "
        "in this conversation, provide your best final answer.\n"
        "Review the observations for:\n"
        "- Pathogen name from lab results\n"
        "- Food with highest relative risk from attack rate analysis\n"
        "- Transmission route\n"
        "- Specific symptoms, onset window, and venue name\n\n"
        "Respond with ONLY this JSON (no other text):\n"
        '{"pathogen": "...", "source": "...", "route": "foodborne", '
        '"case_definition": {"clinical": "...", "time": "...", "place": "..."}}'
    )
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages + [{"role": "user", "content": synthesis_prompt}],
            max_tokens=400,
            temperature=0.0,
        )
        raw = response.choices[0].message.content or ""
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"[DEBUG] LLM final answer synthesis error: {e}", flush=True)
    # Absolute fallback — still provides meaningful case definition fields
    return {
        "pathogen": "unknown",
        "source": "unknown",
        "route": "foodborne",
        "case_definition": {
            "clinical": "gastrointestinal illness with nausea and diarrhea",
            "time": "hours to days after shared meal at event",
            "place": "shared meal event venue",
        },
    }


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
            {
                "role": "user",
                "content": (
                    f"New outbreak investigation:\n\n{alert}\n\n"
                    "Begin your investigation following the strategy in your instructions."
                ),
            },
        ]

        for turn in range(1, max_turns + 1):
            assistant_msg = get_llm_action(messages)

            if not assistant_msg:
                # LLM failed — break and force-submit from context
                break

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
                log_step(
                    step=turn, action=command, reward=reward,
                    done=done, error=error_msg,
                )
                break

            rewards.append(reward)
            steps_taken = turn
            log_step(
                step=turn, action=command, reward=reward,
                done=done, error=error_msg,
            )

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

            # Use LLM to synthesize a final answer from accumulated evidence
            final_params = get_llm_final_answer(messages)

            try:
                result = env_step("submit_final_answer", final_params)
                reward = float(result["reward"])
                score = reward
                done = True
            except Exception as e:
                error_msg = str(e)[:100]
                reward = 0.0
                score = 0.0
                done = True

            rewards.append(reward)
            steps_taken = turn
            success = score >= SUCCESS_SCORE_THRESHOLD
            log_step(
                step=turn, action="submit_final_answer",
                reward=reward, done=done, error=error_msg,
            )

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
            log_end(success=False, steps=0, score=0.0, rewards=[])
            all_scores[task] = 0.0

    print(
        f"\n[DEBUG] FINAL SCORES: easy={all_scores.get('easy', 0):.3f} "
        f"medium={all_scores.get('medium', 0):.3f} "
        f"hard={all_scores.get('hard', 0):.3f}",
        flush=True,
    )
