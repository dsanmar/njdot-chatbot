"""Vector similarity search for NJDOT chunks.

Provides ``VectorSearcher``, the retrieval layer for the chatbot RAG pipeline.

How it works
------------
1. The query string is embedded with ``text-embedding-3-small`` (same model
   used at ingest time) to produce a 1536-dimensional vector.
2. The vector is passed to the ``match_chunks`` PostgreSQL function already
   deployed in Supabase.  That function performs a cosine-similarity search
   over the ``chunks`` table using the ``pgvector`` index.
3. Results are filtered by an optional ``collection`` parameter and a
   minimum similarity ``threshold``, then returned as a list of dicts.

Supabase RPC signature (expected)
----------------------------------
    match_chunks(
        query_embedding  vector(1536),
        match_count      int      default 10,
        filter_collection text     default null,
        match_threshold  float8   default 0.0
    )
    returns table(
        id          uuid,
        content     text,
        metadata    jsonb,
        similarity  float8,
        collection  text
    )

Result dict schema
------------------
Each element returned by ``search()`` has:

    id          str   – UUID of the row in ``chunks``
    content     str   – chunk text
    metadata    dict  – {doc, section_id, section_title, division,
                         page_pdf, page_printed, kind}
    similarity  float – cosine similarity in [0, 1]
    collection  str   – "specs_2019" | "scheduling" | "material_procs"

Usage
-----
    from app.retrieval.vector_search import VectorSearcher

    searcher = VectorSearcher()
    results  = searcher.search(
        "What are the proposal bond requirements?",
        collection="specs_2019",
        match_count=5,
        threshold=0.3,
    )
    for r in results:
        print(r["similarity"], r["metadata"]["section_id"])
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Package-root import shim (supports both -m and direct script execution) ───
try:
    from app.config   import config
    from app.database import get_db
except ImportError:
    _pkg_root = str(Path(__file__).resolve().parent.parent.parent)
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)
    from app.config   import config  # type: ignore[no-redef]
    from app.database import get_db  # type: ignore[no-redef]

import openai


# ── Module-level constants ────────────────────────────────────────────────────

_RPC_FUNCTION: str = "match_chunks"


# ── Main class ────────────────────────────────────────────────────────────────

class VectorSearcher:
    """
    Embed a query and retrieve the most similar chunks from Supabase.

    Parameters
    ----------
    api_key : str or None
        OpenAI API key.  ``None`` → read from ``Config.OPENAI_API_KEY``.
    model : str
        Embedding model (default ``Config.EMBEDDING_MODEL``,
        i.e. ``"text-embedding-3-small"``).
    db_client : supabase.Client or None
        Supabase client to use.  ``None`` → obtain from ``get_db()``.
    """

    def __init__(
        self,
        api_key:   str | None = None,
        model:     str        = config.EMBEDDING_MODEL,
        db_client: Any | None = None,
    ) -> None:
        _key = api_key or config.OPENAI_API_KEY
        if not _key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY in .env or pass api_key= explicitly."
            )
        self._oai_client = openai.OpenAI(api_key=_key)
        self._model      = model
        self._db         = db_client if db_client is not None else get_db()

    # ── Public ────────────────────────────────────────────────────────────────

    def search(
        self,
        query:       str,
        collection:  Optional[str] = None,
        match_count: int           = 10,
        threshold:   float         = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Embed *query* and return the top matching chunks.

        Parameters
        ----------
        query : str
            Natural-language question or search phrase.
        collection : str or None
            Restrict results to this collection (``"specs_2019"``,
            ``"scheduling"``, or ``"material_procs"``).  ``None`` → search
            across all collections.
        match_count : int
            Maximum number of results to return (default 10).
        threshold : float
            Minimum cosine similarity required (default 0.3).  Results below
            this value are excluded by the SQL function.

        Returns
        -------
        list[dict]
            Ordered by descending similarity.  Each dict has:
            ``id``, ``content``, ``metadata``, ``similarity``, ``collection``.
        """
        embedding = self._embed_query(query)
        return self._rpc_search(embedding, collection, match_count, threshold)

    # ── Private ───────────────────────────────────────────────────────────────

    def _embed_query(self, query: str) -> List[float]:
        """Return the 1536-dimensional embedding for *query*."""
        response = self._oai_client.embeddings.create(
            model=self._model,
            input=[query],
        )
        return response.data[0].embedding

    def _rpc_search(
        self,
        embedding:   List[float],
        collection:  Optional[str],
        match_count: int,
        threshold:   float,
    ) -> List[Dict[str, Any]]:
        """
        Call the ``match_chunks`` Supabase RPC function and normalise results.

        The RPC call passes ``None`` for ``filter_collection`` when no
        collection filter is requested; the SQL function treats ``NULL`` as
        "no filter" and searches all collections.
        """
        params: Dict[str, Any] = {
            "query_embedding":   embedding,
            "match_count":       match_count,
            "filter_collection": collection,   # None → SQL NULL → no filter
            "match_threshold":   threshold,
        }

        response = self._db.rpc(_RPC_FUNCTION, params).execute()

        results: List[Dict[str, Any]] = []
        for row in response.data:
            results.append({
                "id":         row.get("id"),
                "content":    row.get("content", ""),
                "metadata":   row.get("metadata", {}),
                "similarity": row.get("similarity", 0.0),
                "collection": row.get("collection", ""),
            })

        return results


# ── Convenience wrapper ───────────────────────────────────────────────────────

def search_chunks(
    query:       str,
    collection:  Optional[str] = None,
    match_count: int           = 10,
    threshold:   float         = 0.3,
) -> List[Dict[str, Any]]:
    """
    One-shot helper: instantiate ``VectorSearcher`` and run a single search.

    Parameters
    ----------
    query : str
        Natural-language search phrase.
    collection : str or None
        Optional collection filter.
    match_count : int
        Maximum results (default 10).
    threshold : float
        Minimum similarity (default 0.3).

    Returns
    -------
    list[dict]
        Matching chunks ordered by descending similarity.
    """
    return VectorSearcher().search(
        query,
        collection=collection,
        match_count=match_count,
        threshold=threshold,
    )
