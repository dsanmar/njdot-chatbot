"""BDCMatcher — look up BDC amendments for given spec section IDs.

Queries the ``bdc_section_map`` table (no embedding, no LLM) and returns
amendment metadata for any sections affected by a Baseline Document Change.

Intended usage in the query pipeline
--------------------------------------
After hybrid retrieval, collect the ``section_id`` values from the top
retrieved chunks, then call ``BDCMatcher.get_amendments(section_ids)`` to
check whether any of those sections have been amended by a BDC.  If so,
inject the amendment info into the prompt so the LLM can surface it.

    from app.retrieval.bdc_matcher import get_bdc_matcher

    matcher    = get_bdc_matcher()
    amendments = matcher.get_amendments(["107.11.01", "902.16", "160.03.01"])
    # → [{"bdc_id": "BDC25S-01", "section_id": "107.11.01", ...}, ...]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    from app.database import get_db
except ImportError:                              # running as script from repo root
    _root = str(Path(__file__).resolve().parent.parent.parent)
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from app.database import get_db  # type: ignore[no-redef]


_SELECT_COLS = (
    "bdc_id,section_id,change_type,amendment_text,"
    "effective_date,implementation_code,bdc_date,subject"
)


class BDCMatcher:
    """
    Pure DB lookup: returns all BDC amendments affecting the given sections.

    Parameters
    ----------
    db_client : supabase.Client or None
        Supabase client.  ``None`` → obtain from ``get_db()``.
    """

    def __init__(self, db_client: Any | None = None) -> None:
        self._db = db_client if db_client is not None else get_db()

    def get_amendments(self, section_ids: list[str]) -> list[dict[str, Any]]:
        """
        Return all BDC amendments that affect any of the given section IDs.

        Parameters
        ----------
        section_ids : list[str]
            Section IDs to check, e.g. ["107.11.01", "902.16", "160.03.01"].
            An empty list returns ``[]`` immediately (no DB round-trip).

        Returns
        -------
        list[dict]
            One dict per matching ``bdc_section_map`` row, with keys:
              bdc_id, section_id, change_type, amendment_text,
              effective_date, implementation_code, bdc_date, subject.
            Ordered by ``bdc_date`` ascending (oldest amendment first).
        """
        if not section_ids:
            return []

        res = (
            self._db
            .table("bdc_section_map")
            .select(_SELECT_COLS)
            .in_("section_id", section_ids)
            .order("bdc_date", desc=False)
            .execute()
        )
        return res.data or []


# ── Module-level singleton ─────────────────────────────────────────────────────

_instance: BDCMatcher | None = None


def get_bdc_matcher() -> BDCMatcher:
    """Return (or create) the module-level ``BDCMatcher`` singleton."""
    global _instance
    if _instance is None:
        _instance = BDCMatcher()
    return _instance
