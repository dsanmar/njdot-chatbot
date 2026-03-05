"""BM25-style keyword search for NJDOT chunks.

Provides ``KeywordSearcher``, a full-text retrieval layer backed by
PostgreSQL's built-in ``tsvector`` / ``tsquery`` machinery.

How it works
------------
1. The *query_text* string is passed to the ``keyword_search_chunks``
   PostgreSQL function already deployed in Supabase.
2. That function converts both document content and the query to
   ``tsvector`` / ``websearch_to_tsquery`` representations and ranks
   matches with ``ts_rank_cd`` (cover-density ranking, a close
   approximation of BM25 for Postgres).
3. An optional ``filter_collection`` parameter restricts the search to a
   single collection.
4. Results are returned with the same dict shape used by ``VectorSearcher``
   so they can be merged by ``HybridRanker`` without special-casing.

Supabase RPC signature (expected)
----------------------------------
    keyword_search_chunks(
        search_query      text,
        match_count       int  default 10,
        filter_collection text default null
    )
    returns table(
        id          uuid,
        content     text,
        metadata    jsonb,
        rank        float8,
        collection  text
    )

See ``sql/keyword_search_chunks.sql`` (or the README) for the exact
``CREATE OR REPLACE FUNCTION`` statement to run in the Supabase SQL editor.

Result dict schema
------------------
Each element returned by ``search()`` has:

    id          str   – UUID of the row in ``chunks``
    content     str   – chunk text
    metadata    dict  – {doc, section_id, section_title, division,
                         page_pdf, page_printed, kind}
    similarity  float – ts_rank_cd score (≥ 0; higher = better match)
    collection  str   – "specs_2019" | "scheduling" | "material_procs"

Usage
-----
    from app.retrieval.bm25_search import KeywordSearcher

    searcher = KeywordSearcher()
    results  = searcher.search(
        "proposal bond requirements",
        collection="specs_2019",
        match_count=5,
    )
    for r in results:
        print(r["similarity"], r["metadata"]["section_id"])
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Package-root import shim ─────────────────────────────────────────────────
try:
    from app.database import get_db
except ImportError:
    _pkg_root = str(Path(__file__).resolve().parent.parent.parent)
    if _pkg_root not in sys.path:
        sys.path.insert(0, _pkg_root)
    from app.database import get_db  # type: ignore[no-redef]


# ── Module-level constants ────────────────────────────────────────────────────

_RPC_FUNCTION: str = "keyword_search_chunks"

# Words that commonly appear in natural-language questions but carry no
# document-matching signal and will break websearch_to_tsquery AND-chains
# if they are not in the target document.  E.g. "allowed" in "What is the
# maximum percentage allowed?" is question phrasing, not a document term.
_QUESTION_STOP_WORDS: frozenset[str] = frozenset({
    "what", "whats", "which", "who", "whom", "whose",
    "when", "where", "why", "how",
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had",
    "can", "could", "may", "might", "must", "shall", "should", "will", "would",
    "the", "a", "an",
    "allowed", "required", "specified", "defined", "described", "stated",
    "used", "given", "listed", "mentioned", "noted", "indicated",
    "provide", "gives", "describe", "explain", "state", "list",
    "tell", "show",
    "please", "per",
})


def _clean_for_bm25(query: str) -> str:
    """
    Strip punctuation and question-phrasing words before handing the query
    to ``websearch_to_tsquery``.

    ``websearch_to_tsquery`` AND-chains every significant token, so if any
    one token is absent from a document the whole document is excluded.
    Question words like "allowed", "required", "what", "is" carry no
    document-content signal but will silently eliminate correct matches.

    Strategy
    --------
    1. Remove punctuation (keeps alphanumeric + spaces).
    2. Lowercase.
    3. Drop tokens in ``_QUESTION_STOP_WORDS``.
    4. Keep remaining tokens joined by spaces (websearch_to_tsquery will
       apply its own stemming and stop-word elimination on top).
    """
    cleaned = re.sub(r"[^\w\s]", " ", query)
    tokens  = [
        t for t in cleaned.lower().split()
        if t not in _QUESTION_STOP_WORDS and len(t) > 1
    ]
    return " ".join(tokens) if tokens else query   # fallback to original


# ── Main class ────────────────────────────────────────────────────────────────

class KeywordSearcher:
    """
    Run full-text keyword search over the ``chunks`` table via Supabase RPC.

    Parameters
    ----------
    db_client : supabase.Client or None
        Supabase client to use.  ``None`` → obtain from ``get_db()``.
    """

    def __init__(self, db_client: Any | None = None) -> None:
        self._db = db_client if db_client is not None else get_db()

    # ── Public ────────────────────────────────────────────────────────────────

    def search(
        self,
        query:       str,
        collection:  Optional[str] = None,
        match_count: int           = 10,
    ) -> List[Dict[str, Any]]:
        """
        Run a full-text keyword search and return ranked results.

        Parameters
        ----------
        query : str
            Natural-language question or keyword phrase.  The Postgres
            ``websearch_to_tsquery`` parser handles multi-word queries,
            quoted phrases (``"proposal bond"``), and negation (``-``).
        collection : str or None
            Restrict results to this collection.  ``None`` → all collections.
        match_count : int
            Maximum number of results to return (default 10).

        Returns
        -------
        list[dict]
            Ordered by descending ``ts_rank_cd`` score.  Each dict has:
            ``id``, ``content``, ``metadata``, ``similarity``, ``collection``.
        """
        return self._rpc_search(query, collection, match_count)

    # ── Private ───────────────────────────────────────────────────────────────

    def _rpc_search(
        self,
        query:       str,
        collection:  Optional[str],
        match_count: int,
    ) -> List[Dict[str, Any]]:
        """
        Call ``keyword_search_chunks`` and normalise the response rows.

        ``None`` for ``filter_collection`` becomes SQL ``NULL``, which the
        function interprets as "no collection filter".
        """
        cleaned_query = _clean_for_bm25(query)
        params: Dict[str, Any] = {
            "search_query":      cleaned_query,
            "match_count":       match_count,
            "filter_collection": collection,
        }

        response = self._db.rpc(_RPC_FUNCTION, params).execute()

        results: List[Dict[str, Any]] = []
        for row in response.data:
            results.append({
                "id":         row.get("id"),
                "content":    row.get("content", ""),
                "metadata":   row.get("metadata", {}),
                # Expose ts_rank_cd score as "similarity" for uniform handling
                "similarity": float(row.get("rank", 0.0)),
                "collection": row.get("collection", ""),
            })

        return results


# ── Convenience wrapper ───────────────────────────────────────────────────────

def keyword_search_chunks(
    query:       str,
    collection:  Optional[str] = None,
    match_count: int           = 10,
) -> List[Dict[str, Any]]:
    """
    One-shot helper: instantiate ``KeywordSearcher`` and run a single search.

    Parameters
    ----------
    query : str
        Natural-language or keyword search phrase.
    collection : str or None
        Optional collection filter.
    match_count : int
        Maximum results (default 10).

    Returns
    -------
    list[dict]
        Matching chunks ordered by descending keyword rank.
    """
    return KeywordSearcher().search(
        query,
        collection=collection,
        match_count=match_count,
    )
