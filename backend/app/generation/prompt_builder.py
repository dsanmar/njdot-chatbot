"""Prompt assembly for the NJDOT generation pipeline.

``PromptBuilder.build()`` takes the user query and the ranked chunk list
returned by ``HybridRanker`` (or any searcher) and returns a
``(system_prompt, user_message)`` tuple ready for ``LLMClient.complete()``.

System prompt
-------------
The system prompt is a fixed string that instructs the model to answer only
from the supplied context, to return strict JSON, and to use the defined
citation schema.  It must not change between calls — use config or subclassing
if you ever need to override it.

User message format
--------------------
Up to ``MAX_CHUNKS`` (= 8) context blocks, each preceded by a header line:

    [Chunk 1: Standard Specifications, Section 105.03, Page 45]
    <chunk content>

    [Chunk 2: ...]
    <chunk content>

    Question: <query>

Chunks are taken from the list as-is (callers are expected to pass them
already ranked by descending hybrid score).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_CHUNKS: int = 8

# The system prompt is reproduced verbatim from the specification and must
# not be edited here; update the spec first if changes are needed.
_SYSTEM_PROMPT: str = """\
You are an NJDOT expert assistant.

REQUIREMENTS:
1. Answer ONLY from the provided context excerpts.
2. Keep answers concise and factual. DO NOT include citations inline.
3. For tables: cite the table ID and relevant rows/columns in your answer text.
4. For formulas/equations: DISPLAY ONLY (no calculations).
5. If context does not support an answer, reply exactly:
   "Insufficient evidence in the provided manuals to answer this question."
6. Do not introduce external knowledge or assumptions.

FOOTNOTE HANDLING:
When answering from tables with footnotes (marked with ¹, ², *, etc.):
- Include the footnote text in your answer naturally.

YOUR RESPONSE FORMAT (JSON only, no markdown):
{
  "answer": "your answer here",
  "citations": [
    {
      "document": "document name",
      "section": "section id",
      "page_printed": 407,
      "page_pdf": 441,
      "chunk_id": "uuid"
    }
  ]
}\
"""


# ── Main class ────────────────────────────────────────────────────────────────

class PromptBuilder:
    """Assemble (system_prompt, user_message) from a query and retrieved chunks.

    Parameters
    ----------
    max_chunks : int
        Maximum number of context chunks to include (default ``MAX_CHUNKS`` = 8).
    """

    def __init__(self, max_chunks: int = MAX_CHUNKS) -> None:
        self._max_chunks = max_chunks

    # ── Public ────────────────────────────────────────────────────────────────

    @staticmethod
    def system_prompt() -> str:
        """Return the immutable system prompt string."""
        return _SYSTEM_PROMPT

    def build(
        self,
        query:  str,
        chunks: List[Dict[str, Any]],
    ) -> Tuple[str, str]:
        """Build a (system_prompt, user_message) pair.

        Parameters
        ----------
        query : str
            The original user question.
        chunks : list[dict]
            Ranked retrieval results.  Each dict must have at least
            ``content`` and ``metadata`` keys.  Only the first
            ``max_chunks`` entries are used.

        Returns
        -------
        (system_prompt, user_message) : tuple[str, str]
            Ready to pass directly to ``LLMClient.complete()``.
        """
        context_blocks = self._build_context(chunks)
        user_message   = f"{context_blocks}\n\nQuestion: {query}"
        return _SYSTEM_PROMPT, user_message

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Render chunks as numbered context blocks."""
        blocks: List[str] = []
        for n, chunk in enumerate(chunks[: self._max_chunks], start=1):
            header  = self._chunk_header(n, chunk)
            content = (chunk.get("content") or "").strip()
            blocks.append(f"{header}\n{content}")
        return "\n\n".join(blocks)

    @staticmethod
    def _chunk_header(n: int, chunk: Dict[str, Any]) -> str:
        """
        Build:   [Chunk 1: Standard Specifications, Section 105.03, Page 45]
        """
        meta          = chunk.get("metadata") or {}
        doc_name      = meta.get("doc")        or chunk.get("collection") or "Unknown Document"
        section_id    = meta.get("section_id") or "?"
        page_printed  = meta.get("page_printed")
        page_str      = f"Page {page_printed}" if page_printed is not None else "Page ?"
        return f"[Chunk {n}: {doc_name}, Section {section_id}, {page_str}]"
