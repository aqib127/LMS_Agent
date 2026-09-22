"""
Multi-provider LLM wrapper.

Providers:
  - ollama     : local, free, offline (default)
  - openai     : cloud (needs OPENAI_API_KEY)
  - anthropic  : cloud (needs ANTHROPIC_API_KEY)
  - none       : returns a placeholder (built-in quick answers still work)
"""
from config.settings import settings
from core.utils import logger


class LLMError(Exception):
    pass


def _ollama_chat(system: str, user: str, model: str | None = None) -> str:
    import ollama
    client = ollama.Client(host=settings.ollama_host)
    resp = client.chat(
        model=model or settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options={"temperature": 0.3},
    )
    msg = resp.get("message") or {}
    return msg.get("content", "").strip()


def _openai_chat(system: str, user: str, model: str | None = None) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=model or settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def _anthropic_chat(system: str, user: str, model: str | None = None) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=model or settings.llm_model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts = []
    for blk in resp.content:
        if getattr(blk, "type", None) == "text":
            parts.append(blk.text)
    return "".join(parts).strip()


def chat(system: str, user: str) -> str:
    provider = (settings.llm_provider or "none").lower()

    if provider == "none":
        return "[LLM disabled: using built-in answers only]"

    try:
        if provider == "ollama":
            logger.debug("LLM call via ollama")
            return _ollama_chat(system, user)
        if provider == "openai":
            if not settings.openai_api_key:
                raise LLMError("OPENAI_API_KEY not set")
            logger.debug("LLM call via openai")
            return _openai_chat(system, user)
        if provider == "anthropic":
            if not settings.anthropic_api_key:
                raise LLMError("ANTHROPIC_API_KEY not set")
            logger.debug("LLM call via anthropic")
            return _anthropic_chat(system, user)
        raise LLMError(f"Unknown provider: {provider}")
    except Exception as e:
        logger.error(f"LLM call failed ({provider}): {e}")
        raise LLMError(str(e))
