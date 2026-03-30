"""Pydantic request/response schemas for the NJDOT Chatbot API.

All models use Pydantic v2.  ``CitationItem`` deliberately accepts extra
fields (``extra="ignore"``) so that the ``verified`` flag emitted by
``CitationSerializer`` is silently dropped at the API boundary — it is an
internal quality signal, not part of the public contract.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ── Request ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Body expected on ``POST /api/query``.

    Blank-query validation is intentionally left to the endpoint handler so
    that the API returns HTTP 400 (not the Pydantic-generated 422).
    """

    query:      str
    collection: Optional[str] = None   # None → search all collections


# ── Citation item ─────────────────────────────────────────────────────────────

class CitationItem(BaseModel):
    """One verified source reference returned with an answer."""

    # Drop internal keys emitted by CitationSerializer (e.g. ``verified``)
    model_config = ConfigDict(extra="ignore")

    document:     Optional[str] = None
    section:      Optional[str] = None
    page_printed: Optional[int] = None
    page_pdf:     Optional[int] = None
    chunk_id:     Optional[str] = None


# ── BDC alert item ────────────────────────────────────────────────────────────

class BDCAlertItem(BaseModel):
    """One Baseline Document Change amendment that affects a retrieved section."""

    bdc_id:              str
    section_id:          str
    effective_date:      Optional[str] = None
    subject:             Optional[str] = None
    implementation_code: Optional[str] = None
    change_type:         Optional[str] = None


# ── Response ──────────────────────────────────────────────────────────────────

class QueryResponse(BaseModel):
    """Body returned by ``POST /api/query``."""

    answer:           str
    citations:        List[CitationItem]
    query_type:       str                  # "semantic" | "keyword-heavy"
    response_time_ms: int
    bdc_alerts:       List[BDCAlertItem] = []  # non-empty when retrieved sections have BDC amendments
