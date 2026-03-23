"""
LLM provider abstraction and Anthropic implementation.

Design decisions:
- Uses anthropic.AsyncAnthropic to avoid blocking FastAPI's event loop.
- Pydantic schemas (MessageExtraction, SuggestionOutput) are the LLM boundary
  types; callers convert them into domain dataclasses.
- 1 retry with 1-second delay on RateLimitError / InternalServerError.
- Callers are responsible for fallback to heuristics on any uncaught exception.
"""

import asyncio
import logging
from typing import List, Optional, Protocol, runtime_checkable

import anthropic

from core.models import LeadProfile, Message
from core.llm.schemas import MessageExtraction, SuggestionOutput
from core.llm.tools import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_TOOL,
    REPLY_SYSTEM_PROMPT,
    REPLY_TOOL,
    build_extraction_messages,
    build_reply_messages,
)

logger = logging.getLogger(__name__)

# Default: Haiku for cost efficiency; override via env vars
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


@runtime_checkable
class LLMProvider(Protocol):
    async def extract_message(
        self,
        text: str,
        history: List[Message],
        response_time_seconds: Optional[int] = None,
    ) -> MessageExtraction: ...

    async def generate_suggestions(
        self,
        profile: LeadProfile,
        approach: str,
        history: List[Message],
        tactics: List[str],
        count: int = 3,
    ) -> List[SuggestionOutput]: ...


class AnthropicLLMProvider:
    """Anthropic Claude backend for extraction and reply drafting."""

    def __init__(
        self,
        api_key: str,
        extraction_model: str = DEFAULT_MODEL,
        reply_model: str = DEFAULT_MODEL,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._extraction_model = extraction_model
        self._reply_model = reply_model

    async def extract_message(
        self,
        text: str,
        history: List[Message],
        response_time_seconds: Optional[int] = None,
    ) -> MessageExtraction:
        messages = build_extraction_messages(text, history, response_time_seconds)

        for attempt in range(2):
            try:
                response = await self._client.messages.create(
                    model=self._extraction_model,
                    max_tokens=512,
                    system=EXTRACTION_SYSTEM_PROMPT,
                    tools=[EXTRACTION_TOOL],
                    tool_choice={"type": "tool", "name": "extract_lead_data"},
                    messages=messages,
                )
                for block in response.content:
                    if block.type == "tool_use" and block.name == "extract_lead_data":
                        return MessageExtraction(**block.input)
                raise ValueError("Anthropic did not return an extract_lead_data tool_use block")

            except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
                if attempt == 0:
                    logger.warning("Anthropic transient error on extraction, retrying: %s", exc)
                    await asyncio.sleep(1)
                    continue
                raise

    async def generate_suggestions(
        self,
        profile: LeadProfile,
        approach: str,
        history: List[Message],
        tactics: List[str],
        count: int = 3,
    ) -> List[SuggestionOutput]:
        messages = build_reply_messages(profile, approach, history, tactics, count)

        for attempt in range(2):
            try:
                response = await self._client.messages.create(
                    model=self._reply_model,
                    max_tokens=1024,
                    system=REPLY_SYSTEM_PROMPT,
                    tools=[REPLY_TOOL],
                    tool_choice={"type": "tool", "name": "generate_reply_suggestions"},
                    messages=messages,
                )
                for block in response.content:
                    if block.type == "tool_use" and block.name == "generate_reply_suggestions":
                        raw = block.input.get("suggestions", [])
                        return [SuggestionOutput(**s) for s in raw]
                raise ValueError("Anthropic did not return a generate_reply_suggestions tool_use block")

            except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
                if attempt == 0:
                    logger.warning("Anthropic transient error on reply generation, retrying: %s", exc)
                    await asyncio.sleep(1)
                    continue
                raise
