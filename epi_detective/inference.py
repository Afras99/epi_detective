"""
EpiDetective LLM Agent — inference.py

Baseline ReAct-style agent for the EpiDetective environment.
Uses the OpenAI Client as required by the hackathon spec.

Environment variables:
    API_BASE_URL  — LLM API endpoint (default: https://router.huggingface.co/v1)
    MODEL_NAME    — Model identifier (default: meta-llama/Llama-3.1-8B-Instruct)
    HF_TOKEN      — Hugging Face / API key
    ENV_URL       — Environment server URL (default: http://localhost:7860)
"""

import json
import os
import re

import requests
from openai import OpenAI

API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

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
THOUGHT: [your reasoning]
ACTION: {"command": "request_line_list", "parameters": {}}

## Strategy:
1. Request line list first (demographics, symptoms, onset times)
2. Request lab results (identifies pathogen)
3. Get exposure histories (what people ate)
4. Calculate attack rates for suspicious foods
5. Submit final answer

Be efficient. Each step costs points."""

AVAILABLE_ACTIONS = [
    "view_initial_alert", "request_line_list", "generate_epi_curve",
    "request_lab_results", "get_exposure_history", "calculate_attack_rate",
    "calculate_odds_ratio", "request_environmental_samples",
    "submit_hypothesis", "submit_final_answer",
]


def env_reset(task_id="easy"):
    resp = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id})
    return resp.json()


def env_step(command, parameters=None):
    resp = requests.post(f"{ENV_URL}/step", json={"command": command, "parameters": parameters or {}})
    return resp.json()


def parse_action(text):
    """Extract action JSON from LLM response text."""
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


def run_task(task_id="easy", max_turns=15):
    print(f"\n{'='*60}")
    print(f"  Task: {task_id}")
    print(f"{'='*60}")

    result = env_reset(task_id)
    alert = result["observation"]["narrative"]
    print(f"\nAlert: {alert[:200]}...")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"New outbreak investigation:\n\n{alert}\n\n"
            "Begin your investigation. Use the ACTION format."
        )},
    ]

    for turn in range(max_turns):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=800,
                temperature=0.2,
            )
            assistant_msg = response.choices[0].message.content or ""
        except Exception as e:
            print(f"  LLM Error: {e}")
            assistant_msg = (
                'ACTION: {"command": "submit_final_answer", '
                '"parameters": {"pathogen": "unknown", "source": "unknown", "route": "foodborne"}}'
            )

        messages.append({"role": "assistant", "content": assistant_msg})

        action = parse_action(assistant_msg)
        print(f"\n  Turn {turn+1}: {action['command']}", end="")
        if action.get("parameters"):
            print(f" ({json.dumps(action['parameters'])[:60]})", end="")
        print()

        result = env_step(action["command"], action.get("parameters", {}))
        obs = result["observation"]
        reward = result["reward"]
        done = result["done"]

        print(f"  → Reward: {reward:.4f} | Done: {done}")
        if obs.get("narrative"):
            print(f"  → {obs['narrative'][:150]}...")

        if done:
            print(f"\n  FINAL SCORE: {reward:.4f}")
            return reward

        obs_text = (
            f"OBSERVATION:\n{obs.get('narrative', '')}\n\n"
            f"Step reward: {obs.get('step_reward', 0):.4f}\n"
            f"Steps remaining: {result['state'].get('steps_remaining', '?')}\n"
            f"Available actions: {', '.join(obs.get('available_actions', []))}"
        )
        messages.append({"role": "user", "content": obs_text})

    print("\n  Max turns reached, forcing submission...")
    result = env_step(
        "submit_final_answer",
        {"pathogen": "unknown", "source": "unknown", "route": "foodborne"},
    )
    print(f"  FINAL SCORE: {result['reward']:.4f}")
    return result["reward"]


if __name__ == "__main__":
    scores = {}
    for task in ["easy", "medium", "hard"]:
        try:
            scores[task] = run_task(task)
        except Exception as e:
            print(f"  Task {task} failed: {e}")
            scores[task] = 0.0

    print(f"\n{'='*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*60}")
    for task, score in scores.items():
        print(f"  {task:8s}: {score:.4f}")
    print(f"  {'Average':8s}: {sum(scores.values())/len(scores):.4f}")
