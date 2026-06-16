"""Helpers for models with chain-of-thought / thinking enabled."""

import re

THINK_TAG_RE = re.compile(
    r"<\s*think\s*>.*?<\s*/\s*think\s*>", re.DOTALL | re.IGNORECASE
)

_THINKING_SUFFIX = (
    "\n\nYou may reason step-by-step internally. "
    "In your FINAL visible answer (after thinking), output ONLY the requested "
    "Python code inside a single ```python ... ``` block — no explanations."
)


def strip_think_tags(text):
    """Remove Qwen/DeepSeek-style thinking blocks embedded in content."""
    if not text:
        return ""
    return THINK_TAG_RE.sub("", text).strip()


def has_code_block(text):
    return bool(text and "```" in text)


def merge_model_response(message):
    """Pick the best text for code evaluation from an API message.

    Thinking models (llama.cpp / Qwen3) may split output across:
    - message.content — final answer (sometimes empty until thinking ends)
    - message.reasoning_content — chain-of-thought (may contain draft code)
    - content may embed ... tags
    """
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""

    content_clean = strip_think_tags(content)

    if has_code_block(content_clean):
        return content_clean, reasoning
    if has_code_block(reasoning):
        return reasoning, reasoning
    if content_clean:
        return content_clean, reasoning
    return reasoning, reasoning


def thinking_system_suffix():
    return _THINKING_SUFFIX
