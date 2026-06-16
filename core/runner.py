"""
Runner — Connects to llama.cpp (OpenAI-compatible API) and executes prompts.
"""

import json
import os
import re
import time
import urllib.request

from core.thinking import merge_model_response, thinking_system_suffix

_CODE_BLOCK_SUFFIX = (
    "\n\nCRITICAL: Your final response MUST contain ONLY the requested code "
    "inside a ```python ... ``` block.\n"
    "Structure your answer as:\n"
    "```python\n"
    "def function_name(args):\n"
    "    # implementation\n"
    "```\n"
    "No explanations, no markdown outside the code block."
)

_SYSTEM_PROMPTS = {
    "generation": (
        "You are an expert software engineer. Write clean, correct, "
        "efficient code."
    ),
    "bug_fixing": (
        "You are an expert software engineer specializing in debugging. "
        "Write clean, correct, efficient code."
    ),
    "refactoring": (
        "You are an expert software engineer specializing in refactoring. "
        "Write clean, correct, efficient code."
    ),
    "sql": (
        "You are an expert Python engineer specializing in SQL/BigQuery. "
        "Write clean, correct, efficient code."
    ),
    "data_processing": (
        "You are an expert Python engineer specializing in data processing. "
        "Write clean, correct, efficient code."
    ),
}

_DEFAULT_SYSTEM_PROMPT = (
    "You are an expert software engineer. Write clean, correct, efficient code."
)


class Runner:
    def __init__(self, config):
        self.max_tokens = config["benchmark"]["max_tokens"]
        self.temperature = config["benchmark"]["temperature"]
        self.timeout = config["benchmark"]["timeout"]

    def run(self, model_cfg, task):
        """Send a task to the model and return the response text + timing."""
        endpoint = model_cfg["endpoint"].rstrip("/")
        model_id = model_cfg.get("model_id", "")
        thinking = model_cfg.get("thinking", False)
        max_tokens = model_cfg.get("max_tokens", self.max_tokens)
        timeout = model_cfg.get("timeout", self.timeout)

        prompt = self._build_prompt(task)
        messages = [
            {"role": "system", "content": self._system_prompt(task, thinking)},
            {"role": "user", "content": prompt},
        ]

        body = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        if model_id:
            body["model"] = model_id

        data = json.dumps(body).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        api_key = model_cfg.get("api_key", "") or os.environ.get("MODEL_API_KEY", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(
            f"{endpoint}/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )

        last_error = None
        for attempt in range(3):
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = json.loads(resp.read().decode())
                elapsed = time.time() - t0
                message = result["choices"][0]["message"]
                text, reasoning = merge_model_response(message)
                usage = result.get("usage", {})
                out = {
                    "text": text,
                    "elapsed": elapsed,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                }
                if reasoning and reasoning != text:
                    out["reasoning_content"] = reasoning
                return out
            except Exception as e:
                last_error = str(e)
                if attempt < 2:
                    time.sleep(2)
                else:
                    return {"error": last_error}

    def _system_prompt(self, task, thinking=False):
        """Return category-specific system prompt with optional task override."""
        if task.get("system_prompt"):
            base = task["system_prompt"]
        else:
            category = task.get("category", "")
            base = _SYSTEM_PROMPTS.get(category, _DEFAULT_SYSTEM_PROMPT)
        suffix = _CODE_BLOCK_SUFFIX
        if thinking:
            suffix = thinking_system_suffix() + suffix
        return base + suffix

    def _build_prompt(self, task):
        """Build the full prompt from a task with F2P/P2P context."""
        parts = [task["instruction"]]

        if task.get("code_context"):
            parts.append(f"\nCódigo atual (contém bugs):\n```\n{task['code_context']}\n```")

        if task.get("fail_to_pass"):
            parts.append(
                "\nSeu código deve passar nestes testes (resolver o bug):\n```\n"
                + "\n".join(task["fail_to_pass"])
                + "\n```"
            )

        if task.get("pass_to_pass"):
            parts.append(
                "\nE não deve quebrar estes testes (sem regressão):\n```\n"
                + "\n".join(task["pass_to_pass"])
                + "\n```"
            )

        if task.get("hints"):
            parts.append(f"\nDica: {task['hints']}")

        if task.get("constraints"):
            parts.append(f"\nRestrições: {task['constraints']}")

        return "\n".join(parts)
