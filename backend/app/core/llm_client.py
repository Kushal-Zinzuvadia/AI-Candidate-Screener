"""
Thin wrapper around Groq / Anthropic / OpenAI APIs.

Primary provider: Groq (free tier, LPU hardware — sub-second latency).
Fallback: set LLM_PROVIDER=anthropic or openai in .env.

Groq free-tier limits: ~30 req/min, ~1,000 req/day (§19 of plan).
Retry-with-backoff is applied automatically to handle transient 429s.
"""
import logging
import time

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # seconds; wait 2s, 4s, 8s on successive failures


def call_llm(system: str, user: str, max_tokens: int = 1500) -> str:
    """Call the configured LLM and return the raw text response.

    Retries up to _MAX_RETRIES times with exponential backoff on rate-limit
    or transient errors — important for Groq's free-tier 30 req/min cap.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            if settings.LLM_PROVIDER == "groq":
                return _call_groq(system, user, max_tokens)
            elif settings.LLM_PROVIDER == "anthropic":
                return _call_anthropic(system, user, max_tokens)
            elif settings.LLM_PROVIDER == "openai":
                return _call_openai(system, user, max_tokens)
            else:
                raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER!r}")
        except ValueError:
            raise  # config errors — don't retry
        except Exception as exc:
            last_exc = exc
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "LLM call failed (attempt %d/%d): %s — retrying in %ds",
                attempt + 1,
                _MAX_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError(f"LLM call failed after {_MAX_RETRIES} attempts") from last_exc


def _call_groq(system: str, user: str, max_tokens: int) -> str:
    from groq import Groq  # lazy import

    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    import anthropic  # lazy import

    client = anthropic.Anthropic(api_key=settings.GROQ_API_KEY)  # reuses the single key field
    message = client.messages.create(
        model=settings.LLM_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text


def _call_openai(system: str, user: str, max_tokens: int) -> str:
    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
