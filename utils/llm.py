"""
Helper for calling the GPT5-nano chat model with a prompt and conversation history.
"""

import json
from typing import Dict, List, Optional, Sequence

try:
    # Load environment variables from a local .env file when available.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional; skip loading if it is not installed.
    pass

from openai import OpenAI

ChatMessage = Dict[str, str]

DEFAULT_MODEL = "gpt-5-nano"
JSON_ONLY_SYSTEM_PROMPT = "You are a strict JSON responder. Reply with a single JSON object and nothing else."

client = OpenAI()


def build_messages(prompt: str, history: Optional[Sequence[ChatMessage]] = None) -> List[ChatMessage]:
    """
    Merge an existing chat history with the latest user prompt.

    The history should be an iterable of dicts like:
    {"role": "user" | "assistant" | "system", "content": "..."}
    """
    messages: List[ChatMessage] = []

    if history:
        for item in history:
            if not isinstance(item, dict) or "role" not in item or "content" not in item:
                raise ValueError("Each history entry must be a dict with 'role' and 'content'.")
            role = str(item["role"]).strip()
            if role not in ("user", "assistant", "system"):
                raise ValueError(f"Unsupported role in history: {role}")
            messages.append({"role": role, "content": str(item["content"])})

    messages.append({"role": "user", "content": prompt})
    return messages


def run_gpt(
    prompt: str,
    history: Optional[Sequence[ChatMessage]] = None,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Call GPT5-nano with the given prompt and conversation history and return the text reply.

    Args:
        prompt: New user input to send.
        history: Prior chat messages (will be sent before the new prompt).
        model: Model name to use; defaults to GPT5-nano.
        temperature: Sampling temperature for creativity control.
        max_tokens: Optional limit for the reply length.
    """
    messages = build_messages(prompt, history)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def run_gpt_json(
    prompt: str,
    history: Optional[Sequence[ChatMessage]] = None,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
    parse_json: bool = True,
):
    """
    Call GPT5-nano, forcing a JSON-only reply. Optionally parse into a Python object.

    Args:
        prompt: New user input to send.
        history: Prior chat messages (will be sent before the new prompt).
        model: Model name to use; defaults to GPT5-nano.
        temperature: Sampling temperature; defaults low to keep JSON stable.
        max_tokens: Optional limit for the reply length.
        parse_json: If True, parse and return a Python object; otherwise return the raw string.
    """
    messages = [{"role": "system", "content": JSON_ONLY_SYSTEM_PROMPT}]
    messages += build_messages(prompt, history)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content.strip()
    if not parse_json:
        return content

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {content}") from exc
