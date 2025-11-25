"""
Helper for calling the GPT5-nano chat model with a prompt and conversation history.
"""

import json
from typing import Dict, List, Optional, Sequence
import os

try:
    # Load environment variables from a local .env file when available.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional; skip loading if it is not installed.
    pass

from openai import OpenAI

ChatMessage = Dict[str, str]

DEFAULT_MODEL = "gpt-4.1-nano"
JSON_ONLY_SYSTEM_PROMPT = (
    "You are a strict JSON responder. Reply with exactly one JSON object and nothing else; "
    "no markdown, no code fences, no prose. If unsure, return an object with an 'error' field."
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI()


def _as_response_input(messages: Sequence[ChatMessage]) -> List[Dict[str, object]]:
    """
    Convert chat-style messages to the structured input expected by the
    Responses API.
    """
    return [
        {
            "role": item["role"],
            "content": [{"type": "input_text", "text": item["content"]}],
        }
        for item in messages
    ]


def _extract_output_text(response) -> str:
    """
    Safely pull the model's text output from a Responses API reply.
    """
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    try:
        return response.output[0].content[0].text.strip()
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise ValueError("Model response did not include text output.") from exc


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
    max_completion_tokens: Optional[int] = None,
) -> str:

    messages = build_messages(prompt, history)

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": msg["role"],
                "content": [{"type": "input_text", "text": msg["content"]}],
            }
            for msg in messages
        ],
        max_output_tokens=max_completion_tokens,
    )

    return response.output[0].content[0].text


def run_gpt_json(
    prompt: str,
    history: Optional[Sequence[ChatMessage]] = None,
    *,
    model: str = DEFAULT_MODEL,
    max_completion_tokens: Optional[int] = None,
):
    messages = build_messages(prompt, history)

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": msg["role"],
                "content": [{"type": "input_text", "text": msg["content"]}],
            }
            for msg in messages
        ],
        max_output_tokens=max_completion_tokens,
    )
    print("DEBUG RAW RESPONSE:", response)

    content = response.output[0].content[0].text
    return json.loads(content)
