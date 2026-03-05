"""FastAPI application entry point for the NJDOT Chatbot API.

Start the server
----------------
From the ``backend/`` directory::

    uvicorn app.main:app --reload           # development
    uvicorn app.main:app --host 0.0.0.0     # production

Interactive docs
----------------
* Swagger UI : http://localhost:8000/docs
* ReDoc      : http://localhost:8000/redoc

Endpoints
---------
GET  /health      → {"status": "ok"}
POST /api/query   → QueryResponse  (see app.api.query)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.query import router as query_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NJDOT Chatbot API",
    description=(
        "RAG-based question-answering API for NJDOT Standard Specifications, "
        "CPM Scheduling requirements, and Material Procedures."
    ),
    version="0.1.0",
)

# ── CORS (allow all origins for PoC) ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(query_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe — returns ``{"status": "ok"}`` with HTTP 200."""
    return {"status": "ok"}


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
