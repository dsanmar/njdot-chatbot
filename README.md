# NJDOT AI Assistant

A RAG (Retrieval-Augmented Generation) chatbot for querying New Jersey Department of Transportation documents — standard specifications, material procedures, and construction scheduling manuals.

Built with **FastAPI** + **pgvector** (Supabase) on the backend and **Next.js 16** + **Supabase Auth** on the frontend.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- A **Supabase** project with the `pgvector` extension enabled and the SQL functions deployed (see `backend/sql/`)
- An **OpenAI API key** (or a local [Ollama](https://ollama.com) instance — see `.env.example`)

---

## Backend Setup & Running

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the env template and fill in your values
cp .env.example .env

# 4. Start the API server
uvicorn app.main:app --reload --port 8000
# Runs at  http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## Frontend Setup & Running

```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Create the local env file
cp .env.local.example .env.local

# 3. Start the dev server
npm run dev
# Runs at http://localhost:3000
```

---

## Running Ingestion (if starting fresh)

Run these from inside the activated virtual environment (`cd backend && source venv/bin/activate`).

```bash
# Ingest all collections (specs, material procedures, scheduling)
python scripts/ingest_specs.py

# Ingest a single collection
python scripts/ingest_specs.py --collection specs_2019
python scripts/ingest_specs.py --collection material_procs
python scripts/ingest_specs.py --collection scheduling

# Dry run — parse and chunk PDFs without writing to the database
python scripts/ingest_specs.py --dry-run

# Deploy (or re-deploy) the SQL functions to Supabase
python scripts/deploy_sql.py

# Smoke-test retrieval against the live database
python scripts/test_retrieval.py
```

Source PDFs live in `backend/data/raw_pdfs/`. Add new documents there before running ingestion.

---

## Project Structure

```
njdot-chatbot/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── query.py              # POST /query endpoint — orchestrates retrieval + generation
│   │   ├── ingestion/
│   │   │   ├── pdf_parser.py         # Extracts text and metadata from PDFs via pdfplumber / PyMuPDF
│   │   │   ├── chunker.py            # Splits text into overlapping chunks with section context
│   │   │   ├── embedder.py           # Generates OpenAI text-embedding-3-small vectors
│   │   │   └── section_detector.py   # Detects and labels section headings within documents
│   │   ├── retrieval/
│   │   │   ├── vector_search.py      # Semantic search via pgvector (cosine similarity)
│   │   │   ├── bm25_search.py        # Full-text keyword search via Postgres tsvector/BM25
│   │   │   └── hybrid_ranker.py      # Combines vector + keyword results with Reciprocal Rank Fusion
│   │   ├── generation/
│   │   │   ├── llm_client.py         # Unified client for OpenAI GPT-4o or local Ollama models
│   │   │   ├── prompt_builder.py     # Builds the RAG system/user prompt from retrieved chunks
│   │   │   └── citation_serializer.py# Formats retrieved chunks into structured citation objects
│   │   ├── config.py                 # Pydantic Settings — loads and validates environment variables
│   │   ├── database.py               # Supabase client singleton
│   │   └── main.py                   # FastAPI app entry point, CORS config, router registration
│   ├── data/
│   │   ├── raw_pdfs/                 # Source NJDOT documents (BDC bulletins, MP series, standard specs)
│   │   └── processed/                # Intermediate artifacts from the ingestion pipeline
│   ├── scripts/
│   │   ├── ingest_specs.py           # CLI runner for the full ingestion pipeline
│   │   ├── deploy_sql.py             # Pushes pgvector SQL functions to Supabase
│   │   └── test_retrieval.py         # Quick smoke test for hybrid search against the live DB
│   ├── sql/
│   │   ├── match_chunks.sql          # Postgres function for pgvector similarity search
│   │   └── keyword_search_chunks.sql # Postgres function for BM25 full-text search
│   ├── .env.example                  # Template — copy to .env and fill in secrets
│   └── requirements.txt              # Python dependencies
│
└── frontend/
    ├── src/
    │   ├── app/                      # Next.js App Router pages
    │   │   ├── page.tsx              # Public landing page
    │   │   ├── login/                # Sign-in page
    │   │   ├── signup/               # Account creation page
    │   │   └── chat/                 # Main chat page (protected — requires auth)
    │   ├── components/
    │   │   ├── auth/                 # LoginForm and SignupForm client components
    │   │   └── chat/                 # ChatInterface (message list, input bar, citations panel)
    │   ├── lib/
    │   │   ├── api.ts                # Typed fetch wrapper for the FastAPI backend
    │   │   ├── types.ts              # Shared TypeScript types (CitationItem, etc.)
    │   │   └── supabase/
    │   │       ├── client.ts         # Browser-side Supabase client (for client components)
    │   │       └── server.ts         # Server-side Supabase client (for server components + middleware)
    │   └── middleware.ts             # Route protection — redirects unauthenticated users to /login
    ├── .env.local.example            # Template — copy to .env.local and fill in values
    └── package.json
```

---
