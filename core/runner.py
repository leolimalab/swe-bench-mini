"""
Runner — Connects to llama.cpp (OpenAI-compatible API) and executes prompts.
"""

import json
import os
import time
import urllib.request


class Runner:
    def __init__(self, config):
        self.max_tokens = config["benchmark"]["max_tokens"]
        self.temperature = config["benchmark"]["temperature"]
        self.timeout = config["benchmark"]["timeout"]

    def run(self, model_cfg, task):
        """Send a task to the model and return the response text + timing."""
        endpoint = model_cfg["endpoint"].rstrip("/")
        model_id = model_cfg.get("model_id", "")

        prompt = self._build_prompt(task)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert software engineer. Write clean, correct, "
                    "efficient code. Return ONLY the requested code inside a "
                    "```python ... ``` block. Do not add extra explanations."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        body = {
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        if model_id:
            body["model"] = model_id

        data = json.dumps(body).encode("utf-8")

        # Build headers with optional API key
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

        for attempt in range(3):
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode())
                elapsed = time.time() - t0
                content = result["choices"][0]["message"]["content"]
                return {
                    "text": content,
                    "elapsed": elapsed,
                    "prompt_tokens": result["usage"]["prompt_tokens"],
                    "completion_tokens": result["usage"]["completion_tokens"],
                }
            except Exception as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    return None

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
