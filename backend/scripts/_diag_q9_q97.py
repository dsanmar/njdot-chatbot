"""
Retrieval diagnosis for Q9 and Q97 in specs_2019_v2.
Shows top-5 chunks from both vector and keyword search, then the merged RRF result.
"""

from __future__ import annotations
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent / ".env")

import json, sys, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import get_db

# ── load eval questions ────────────────────────────────────────────────────
EVAL_FILE = ROOT / "data/eval/njdot_eval_set_100_questions.json"
questions  = json.loads(EVAL_FILE.read_text())

TARGETS = {9, 97}
questions = questions["questions"]   # unwrap dict wrapper
target_qs = {q["id"]: q for q in questions if q["id"] in TARGETS}

db = get_db()
COLLECTION = "specs_2019_v2"
TOP_N      = 5


def _bm25_search(query: str, collection: str, top_n: int) -> list[dict]:
    """Full-text (ts_rank) search via keyword_search_chunks RPC."""
    res = db.rpc("keyword_search_chunks", {
        "search_query":      query,
        "filter_collection": collection,
        "match_count":       top_n,
    }).execute()
    return res.data or []


def _vector_search(query: str, collection: str, top_n: int) -> list[dict]:
    """Vector similarity search via match_chunks RPC."""
    from app.config import config
    import openai
    oai  = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    resp = oai.embeddings.create(model=config.EMBEDDING_MODEL, input=[query])
    vec  = resp.data[0].embedding

    res = db.rpc("match_chunks", {
        "query_embedding":   vec,
        "filter_collection": collection,
        "match_count":       top_n,
        "match_threshold":   0.0,
    }).execute()
    return res.data or []


def _fmt_chunk(rank: int, row: dict, source: str = "") -> str:
    m        = row.get("metadata", {})
    sec      = m.get("section_id", "?")
    kind     = m.get("kind", "?")
    table_id = m.get("table_id", "")
    patch    = m.get("_patch", "")
    score    = row.get("similarity") or row.get("rank") or row.get("score", "")
    label    = f"[{table_id}]" if table_id else ""
    patched  = " 🔧PATCH" if patch else ""

    preview = textwrap.shorten(row.get("content", ""), width=200, placeholder="…")

    return (
        f"  #{rank:02d}  sec={sec:<20} kind={kind:<8} {label:<18}{patched}\n"
        f"        score={score!r:<12} {source}\n"
        f"        {preview}\n"
    )


def diagnose(q_id: str, q: dict) -> None:
    query = q["query"]
    gold  = q["gold_answer"]

    print("=" * 70)
    print(f"  Q{q_id}: {query}")
    print(f"  GOLD: {gold}")
    print("=" * 70)

    # ── Vector search ──────────────────────────────────────────────────────
    print(f"\n  ── Vector search (top {TOP_N}) ──")
    vec_rows = _vector_search(query, COLLECTION, TOP_N)
    for i, row in enumerate(vec_rows, 1):
        print(_fmt_chunk(i, row, "vector"))

    # ── BM25 / keyword search ─────────────────────────────────────────────
    print(f"\n  ── Keyword (BM25) search (top {TOP_N}) ──")
    try:
        bm25_rows = _bm25_search(query, COLLECTION, TOP_N)
        for i, row in enumerate(bm25_rows, 1):
            print(_fmt_chunk(i, row, "bm25"))
    except Exception as e:
        print(f"  ⚠️  BM25 search failed: {e}")
        bm25_rows = []

    # ── Summary: which sections appear in BOTH? ────────────────────────────
    vec_secs  = {r.get("metadata", {}).get("section_id") for r in vec_rows}
    bm25_secs = {r.get("metadata", {}).get("section_id") for r in bm25_rows}
    overlap   = vec_secs & bm25_secs
    print(f"\n  ── Section overlap (vector ∩ bm25): {overlap or '(none)'}")

    # ── Check if 902.02.02 appears at all ─────────────────────────────────
    all_rows = vec_rows + bm25_rows
    found_correct = [
        r for r in all_rows
        if "902.02.02" in r.get("metadata", {}).get("section_id", "")
        or "902.02.02-1" in r.get("metadata", {}).get("table_id", "")
    ]
    print(f"\n  ── 902.02.02 chunk in results? {'✅ YES – ' + str(len(found_correct)) + ' hit(s)' if found_correct else '❌ NO'}")
    for r in found_correct:
        m = r.get("metadata", {})
        print(f"        sec={m.get('section_id')}  table_id={m.get('table_id')}  "
              f"patch={bool(m.get('_patch'))}")

    # ── Check if 902.13 appears ────────────────────────────────────────────
    found_902_13 = [
        r for r in all_rows
        if str(r.get("metadata", {}).get("section_id", "")).startswith("902.13")
    ]
    print(f"\n  ── 902.13 HIGH RAP in results? "
          f"{'⚠️  YES – ' + str(len(found_902_13)) + ' hit(s)' if found_902_13 else '✅ NO'}")
    for r in found_902_13:
        m = r.get("metadata", {})
        print(f"        sec={m.get('section_id')}  kind={m.get('kind')}  "
              f"content[:80]={r.get('content','')[:80]!r}")

    print()


# ── run ───────────────────────────────────────────────────────────────────
for qid in (9, 97):
    if qid in target_qs:
        diagnose(qid, target_qs[qid])
    else:
        print(f"⚠️  {qid} not found in eval set\n")
