"""
Thin LLM routing layer.

Supports two backends:
  "claude"  — Anthropic API (requires api_key)
  "local"   — LM Studio OpenAI-compatible endpoint at localhost:1234
               (requires LM Studio running with Gemma-4 loaded, no API key needed)
"""

import requests
import anthropic

LM_STUDIO_BASE_URL = "http://localhost:1234/v1/chat/completions"
LM_STUDIO_MODEL    = (
    "lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf"
)


def chat(
    user_msg: str,
    *,
    system: str = "",
    api_key: str = "",
    model_backend: str = "claude",
    claude_model: str = "claude-sonnet-4-6",
    max_tokens: int = 1500,
) -> str:
    """Send a chat request to the selected backend and return the response text."""

    if model_backend == "local":
        return _lm_studio_chat(system, user_msg, max_tokens)
    else:
        return _claude_chat(system, user_msg, api_key, claude_model, max_tokens)


def _lm_studio_chat(system: str, user_msg: str, max_tokens: int) -> str:
    # LM Studio / Gemma requires a single user message — fold system into it
    content = f"{system}\n\n---\n\n{user_msg}" if system else user_msg
    messages = [{"role": "user", "content": content}]

    resp = requests.post(
        LM_STUDIO_BASE_URL,
        json={"model": LM_STUDIO_MODEL, "messages": messages, "max_tokens": max_tokens},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _claude_chat(system: str, user_msg: str, api_key: str, model: str, max_tokens: int) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_msg}],
    }
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return resp.content[0].text
