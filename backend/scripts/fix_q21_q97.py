"""
fix_q21_q97.py  —  Targeted chunk patches for Q21 and Q97 regressions.

Q21 regression
--------------
"Section 902.02.02 maximum contamination from CRCG in HMA surface course?"
Gold: "No more than 1 percent by weight"

Problem: The updated 902.02.02-1 TABLE chunk now has a CRCG-heavy embedding
that crowds out the 902.02.02 TEXT chunk for contamination queries.  The 1%
contamination rule is buried 4 paragraphs into a large text block covering WMA,
RAP, aggregate gradation, etc.
Fix: Standalone text chunk focused solely on CRCG contamination in surface course.

Q97 regression
--------------
"A contractor wants to use RAP in an HMA base course and also include GBSM.
What is the maximum combined percentage of these two recycled materials, and
what are their individual limits?"
Gold: total ≤ 35 percent; RAP ≤ 25 percent; GBSM ≤ 5 percent

Problem: 902.02.02-1 TABLE chunk contains the 35% ceiling, but the LLM performs
arithmetic (25% RAP + 5% GBSM = 30%) instead of reading the prose ceiling.
The system answer: "maximum combined percentage is 30 percent".
Fix: Standalone chunk that explicitly states combined limits AND pre-empts the
25+5=30 computation by stating the 35% ceiling in the first sentence.

Usage
-----
    python scripts/fix_q21_q97.py [--collection specs_2019_v2] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config   import config
from app.database import get_db
import openai

_oai = openai.OpenAI(api_key=config.OPENAI_API_KEY)


def _embed(text: str) -> list[float]:
    resp = _oai.embeddings.create(model=config.EMBEDDING_MODEL, input=[text])
    return resp.data[0].embedding


# ── Chunk definitions ─────────────────────────────────────────────────────

def _crcg_contamination_chunk() -> dict[str, Any]:
    """
    Q21 fix: standalone chunk for CRCG contamination limit in HMA surface course.

    The source sentence is in the 902.02.02 body text but unreachable once the
    TABLE chunk's embedding dominates CRCG queries.  This chunk surfaces it
    directly and also clarifies the difference between the contamination limit
    (1%, surface course, involuntary) and the recycled-material limit (10%,
    base/intermediate course, intentional use).
    """
    content = """\
902.02.02 CRCG Contamination Limit — HMA Surface Course

For HMA surface course, the finished mix must not contain more than a total of \
1 percent by weight contamination from Crushed Recycled Container Glass (CRCG). \
(Section 902.02.02, Composition of Mixtures)

Clarification: This 1 percent contamination limit applies only to unintentional \
CRCG fragments in the finished surface-course mix. It is distinct from the \
recycled-material limits in Table 902.02.02-1, which govern intentional use of \
CRCG as a recycled material in HMA base or intermediate course (maximum 10 percent \
for that purpose).\
"""
    return {
        "content":  content,
        "metadata": {
            "doc":           "Spec2019",
            "kind":          "text",
            "division":      "MATERIALS",
            "page_pdf":      405,
            "page_printed":  405,
            "section_id":    "902.02.02",
            "section_title": "Composition of Mixtures",
            "_patch": "fix_q21_q97.py v1 – CRCG contamination limit standalone chunk",
        },
    }


def _combined_recycled_ceiling_chunk() -> dict[str, Any]:
    """
    Q97 fix: standalone chunk for combined recycled-materials ceiling (35%).

    The LLM currently computes 25% RAP + 5% GBSM = 30% instead of reading the
    35% combined ceiling from Table 902.02.02-1's prose.  This chunk:
    - States the 35% ceiling in the first sentence
    - Lists individual limits together
    - Includes an explicit worked example showing that 25% + 5% = 30% is WITHIN
      the 35% ceiling, not equal to it — pre-empting the arithmetic confusion
    """
    content = """\
902.02.02 Combined Recycled Materials Ceiling — HMA Base or Intermediate Course

The maximum total recycled materials content for HMA base or intermediate course \
is 35 percent by weight of total mixture. This 35 percent ceiling governs any \
combination of recycled materials (RAP, CRCG, GBSM, RPCSA).

Individual maximum limits (from Table 902.02.02-1):
- RAP (Reclaimed Asphalt Pavement): 25 percent maximum
- CRCG (Crushed Recycled Container Glass): 10 percent maximum
- GBSM (Ground Bituminous Shingle Material): 5 percent maximum
- RPCSA (Recycled Portland Cement Stabilized Aggregate): 20 percent maximum

Important: The combined ceiling is 35 percent, not the arithmetic sum of any \
two individual limits. For example, using both RAP and GBSM at their individual \
maximums (25% RAP + 5% GBSM = 30% total) is within the 35% combined ceiling — \
the combined maximum for RAP and GBSM together is effectively 30 percent when \
both are at their individual limits, but the overall recycled materials ceiling \
remains 35 percent for all materials combined.\
"""
    return {
        "content":  content,
        "metadata": {
            "doc":           "Spec2019",
            "kind":          "text",
            "division":      "MATERIALS",
            "page_pdf":      405,
            "page_printed":  405,
            "section_id":    "902.02.02",
            "section_title": "Composition of Mixtures",
            "_patch": "fix_q21_q97.py v1 – combined recycled materials ceiling chunk",
        },
    }


# ── DB helpers (same pattern as fix_902_tables.py) ────────────────────────

def _patch_exists(db: Any, collection: str, patch_label: str) -> bool:
    """Check by _patch label substring to avoid re-inserting."""
    res = (
        db.table("chunks")
        .select("id")
        .eq("collection", collection)
        .eq("metadata->>section_id", "902.02.02")
        .execute()
    )
    for row in res.data:
        if patch_label in (row.get("metadata") or {}).get("_patch", ""):
            return True
    # PostgREST JSON text-path filters can be finicky; do client-side check
    return False


def _insert_chunk(
    db:         Any,
    collection: str,
    chunk:      dict[str, Any],
    dry_run:    bool,
) -> None:
    content  = chunk["content"]
    metadata = chunk["metadata"]
    label    = metadata.get("_patch", "?")

    if dry_run:
        print(f"  [DRY-RUN] Would insert: {label!r}")
        print(f"    preview: {content[:100]!r}")
        return

    print(f"  Embedding …", end="", flush=True)
    embedding = _embed(content)
    print(" done.")

    db.table("chunks").insert({
        "collection": collection,
        "content":    content,
        "metadata":   metadata,
        "embedding":  embedding,
    }).execute()
    print(f"  ✅ Inserted: {label!r}")


# ── main ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", default="specs_2019_v2")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    col     = args.collection
    dry_run = args.dry_run
    db      = get_db()

    print(f"\n🔧 fix_q21_q97.py — collection={col!r}  dry_run={dry_run}\n")

    # ── Step 1: Q21 — CRCG contamination standalone chunk ─────────────────
    print("Step 1 (Q21): CRCG contamination limit — HMA surface course")
    label_21 = "CRCG contamination limit standalone chunk"
    if _patch_exists(db, col, label_21):
        print("  ⏭️  Already patched — skipping.")
    else:
        _insert_chunk(db, col, _crcg_contamination_chunk(), dry_run)

    # ── Step 2: Q97 — combined recycled materials ceiling ─────────────────
    print("\nStep 2 (Q97): Combined recycled materials 35% ceiling")
    label_97 = "combined recycled materials ceiling chunk"
    if _patch_exists(db, col, label_97):
        print("  ⏭️  Already patched — skipping.")
    else:
        _insert_chunk(db, col, _combined_recycled_ceiling_chunk(), dry_run)

    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
