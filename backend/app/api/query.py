"""POST /api/query — the single RAG endpoint for the NJDOT Chatbot.

Pipeline (per request)
----------------------
1. HybridRanker   – retrieves the top-5 chunks via RRF (vector + keyword)
2. PromptBuilder  – assembles the system prompt and user message
3. LLMClient      – calls gpt-4o-mini with temperature=0
4. CitationSerializer – parses JSON response and validates citations

All pipeline objects are module-level singletons initialised once when
the module is first imported (i.e. when uvicorn loads the app).  They
share a single Supabase client and a single OpenAI client to avoid
redundant connection handshakes.

Error policy
------------
* HTTP 400 – ``query`` field is missing, empty, or blank
  (enforced by the Pydantic ``QueryRequest`` validator before reaching here)
* HTTP 500 – any unexpected exception raised inside the pipeline;
  the ``detail`` string includes the exception type and message so the
  caller can log it without inspecting server logs.
"""

from __future__ import annotations

import time
import logging
from typing import List

from fastapi import APIRouter, HTTPException

from app.database                        import get_db
from app.retrieval.vector_search         import VectorSearcher
from app.retrieval.bm25_search           import KeywordSearcher
from app.retrieval.hybrid_ranker         import HybridRanker, classify_query
from app.retrieval.bdc_matcher           import get_bdc_matcher
from app.generation.llm_client           import LLMClient
from app.generation.prompt_builder       import PromptBuilder
from app.generation.citation_serializer  import CitationSerializer
from app.models                          import BDCAlertItem, CitationItem, QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

# ── Pipeline singletons (initialised once at import time) ─────────────────────
#
# Sharing db_client and oai_client across components avoids opening more
# than one connection to Supabase and one to OpenAI per worker process.
#
_db          = get_db()
_vector      = VectorSearcher(db_client=_db)
_keyword     = KeywordSearcher(db_client=_db)
_hybrid      = HybridRanker(vector_searcher=_vector, keyword_searcher=_keyword)
_bdc_matcher = get_bdc_matcher()
_builder     = PromptBuilder()
_llm         = LLMClient()
_serializer  = CitationSerializer()

# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api")

_RETRIEVE_K: int = 5   # chunks passed to the LLM context


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Ask a question about NJDOT specifications",
    description=(
        "Runs hybrid retrieval (vector + BM25) → prompt assembly → "
        "gpt-4o-mini generation → citation validation and returns a "
        "structured JSON answer with source citations."
    ),
)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """
    End-to-end RAG endpoint.

    Parameters
    ----------
    request : QueryRequest
        ``{"query": "...", "collection": "specs_2019" | null}``

    Returns
    -------
    QueryResponse
        ``{"answer": "...", "citations": [...], "query_type": "...",
           "response_time_ms": N}``

    Raises
    ------
    HTTPException 400
        If the query is empty (caught by Pydantic before reaching here).
    HTTPException 500
        If any step in the pipeline raises an unexpected exception.
    """
    t_start = time.time()

    # Pydantic already validated / stripped the query; double-check anyway.
    query      = request.query.strip()
    collection = request.collection

    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty or blank")

    # ── Query classification (for the response metadata field) ─────────────
    _v, _k, query_type = classify_query(query)

    amendments: list = []   # populated inside try; kept here for scope in response build

    try:
        # ── Step 1: Hybrid retrieval ──────────────────────────────────────
        chunks = _hybrid.search(query, collection=collection, match_count=_RETRIEVE_K)

        # ── Step 1.5: BDC amendment lookup ───────────────────────────────
        # Collect unique section_ids from retrieved chunks, then check
        # bdc_section_map for any amendments affecting those sections.
        section_ids = list({
            c["metadata"].get("section_id")
            for c in chunks
            if c.get("metadata", {}).get("section_id")
        })
        amendments = _bdc_matcher.get_amendments(section_ids)

        # ── Step 2: Prompt assembly ───────────────────────────────────────
        system_prompt, user_message = _builder.build(query, chunks, amendments=amendments)

        # ── Step 3: LLM generation ────────────────────────────────────────
        raw_response = _llm.complete(system_prompt, user_message)

        # ── Step 4: Parse + validate citations ───────────────────────────
        result = _serializer.serialize(raw_response, chunks)

    except Exception as exc:                              # noqa: BLE001
        logger.exception("Pipeline error for query=%r collection=%r", query, collection)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error [{type(exc).__name__}]: {exc}",
        ) from exc

    # ── Build response ─────────────────────────────────────────────────────
    elapsed_ms = int((time.time() - t_start) * 1000)

    answer    = result.get("answer", "")
    raw_cites = result.get("citations") or []

    # If CitationSerializer fell back (parse_error), citations is already []
    citations: List[CitationItem] = [CitationItem(**c) for c in raw_cites]

    # Build BDC alert list (summary fields only — amendment_text goes to LLM, not client)
    bdc_alerts: List[BDCAlertItem] = [
        BDCAlertItem(
            bdc_id=a["bdc_id"],
            section_id=a["section_id"],
            effective_date=str(a.get("effective_date") or ""),
            subject=a.get("subject") or "",
            implementation_code=a.get("implementation_code") or "",
            change_type=a.get("change_type") or None,
        )
        for a in amendments
    ]

    return QueryResponse(
        answer=answer,
        citations=citations,
        query_type=query_type,
        response_time_ms=elapsed_ms,
        bdc_alerts=bdc_alerts,
    )
