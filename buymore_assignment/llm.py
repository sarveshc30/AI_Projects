"""Groq LLM client with a two-key fallback.

Same pattern used in the Kalpi assignment: a Runnable subclass wrapping two ChatGroq
clients, so `prompt | llm` works natively and a rate-limited/expired primary key
transparently rolls over to the secondary instead of failing the run.
"""

import os

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq

FALLBACK_EXCEPTIONS = (
    AuthenticationError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)

load_dotenv()

_GROQ_KEY_1 = os.getenv("GROQ_API_KEY_1")
_GROQ_KEY_2 = os.getenv("GROQ_API_KEY_2")
_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class _FallbackLLM(Runnable):
    """Drop-in ChatGroq replacement that falls back to a secondary key on recoverable errors."""

    def __init__(self, key1, key2, model):
        self._primary = ChatGroq(model=model, api_key=key1)
        self._secondary = ChatGroq(model=model, api_key=key2)
        self._model = model
        self._primary_key_used = True

    def invoke(self, input, config=None, **kwargs):
        try:
            result = self._primary.invoke(input, config=config, **kwargs)
            self._primary_key_used = True
            return result
        except FALLBACK_EXCEPTIONS as e:
            print(f"Primary API key failed ({type(e).__name__}): {str(e)[:100]}. Switching to secondary key.")
            try:
                result = self._secondary.invoke(input, config=config, **kwargs)
                self._primary_key_used = False
                print("Secondary API key succeeded.")
                return result
            except FALLBACK_EXCEPTIONS as e2:
                raise RuntimeError(
                    f"Both API keys exhausted.\n"
                    f"Primary error: {type(e).__name__}: {str(e)[:200]}\n"
                    f"Secondary error: {type(e2).__name__}: {str(e2)[:200]}\n"
                    f"Debugging steps:\n"
                    f"1. Check GROQ_API_KEY_1 and GROQ_API_KEY_2 in .env\n"
                    f"2. Verify keys are valid at https://console.groq.com\n"
                    f"3. Check for rate limit: https://console.groq.com/docs/rate-limits\n"
                    f"4. Check network connectivity\n"
                    f"5. Try again in a few minutes (transient error)"
                ) from e2

    def with_structured_output(self, schema, **kwargs):
        """Pass structured output through to both primary and secondary clients."""
        # __new__ avoids re-constructing the two ChatGroq clients from scratch.
        bound = _FallbackLLM.__new__(_FallbackLLM)
        bound._primary = self._primary.with_structured_output(schema, **kwargs)
        bound._secondary = self._secondary.with_structured_output(schema, **kwargs)
        bound._model = self._model
        bound._primary_key_used = True
        return bound


def get_llm():
    """Build the LLM lazily so the scraping-only paths still run without Groq keys set."""
    if not _GROQ_KEY_1 or not _GROQ_KEY_2:
        raise EnvironmentError(
            "GROQ_API_KEY_1 and GROQ_API_KEY_2 must both be set in your .env file."
        )
    return _FallbackLLM(_GROQ_KEY_1, _GROQ_KEY_2, _MODEL)


def llm_available():
    return bool(_GROQ_KEY_1 and _GROQ_KEY_2)
