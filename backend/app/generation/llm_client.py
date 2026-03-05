"""OpenAI chat-completion client for NJDOT generation.

Wraps ``openai.OpenAI.chat.completions.create`` with a minimal, injectable
interface.  All callers share a single ``openai.OpenAI`` client instance when
they pass one in; otherwise a fresh client is constructed from config.

Usage
-----
    from app.generation.llm_client import LLMClient

    client = LLMClient()
    text = client.complete(system_prompt="You are …", user_message="…")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import openai

# ── Package-root import shim ──────────────────────────────────────────────────
try:
    from app.config import config
except ImportError:
    _pkg_root = str(Path(__file__).resolve().parent.parent.parent)
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)
    from app.config import config  # type: ignore[no-redef]


_DEFAULT_MODEL = "gpt-4o-mini"


class LLMClient:
    """Thin wrapper around OpenAI chat completions.

    Parameters
    ----------
    api_key : str or None
        OpenAI API key.  ``None`` → read from ``config.OPENAI_API_KEY``.
    model : str or None
        Chat model name.  ``None`` → use ``config.CHAT_MODEL`` (default
        ``"gpt-4o-mini"``).
    oai_client : openai.OpenAI or None
        Pre-built OpenAI client to reuse.  When supplied, ``api_key`` is
        ignored.
    """

    def __init__(
        self,
        api_key:    Optional[str]          = None,
        model:      Optional[str]          = None,
        oai_client: Optional[openai.OpenAI] = None,
    ) -> None:
        if oai_client is not None:
            self._client = oai_client
        else:
            _key = api_key or config.OPENAI_API_KEY
            if not _key:
                raise ValueError(
                    "OpenAI API key is required. "
                    "Set OPENAI_API_KEY in .env or pass api_key= to LLMClient."
                )
            self._client = openai.OpenAI(api_key=_key)

        self._model: str = model or getattr(config, "CHAT_MODEL", _DEFAULT_MODEL)

    # ── Public ────────────────────────────────────────────────────────────────

    @property
    def model(self) -> str:
        """The chat model name in use."""
        return self._model

    def complete(self, system_prompt: str, user_message: str) -> str:
        """Run a single-turn chat completion and return the raw response text.

        Parameters
        ----------
        system_prompt : str
            System-role instructions handed to the model.
        user_message : str
            The user turn: assembled context chunks + question.

        Returns
        -------
        str
            Raw text from ``choices[0].message.content``.

        Raises
        ------
        RuntimeError
            Wraps any ``openai.OpenAIError`` with a descriptive prefix so
            callers can log the failure clearly without importing openai
            error types themselves.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
            )
            return response.choices[0].message.content or ""

        except openai.OpenAIError as exc:
            raise RuntimeError(
                f"LLM completion failed [{type(exc).__name__}]: {exc}"
            ) from exc
