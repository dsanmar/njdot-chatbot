"""
fix_902_tables.py  —  Patch specs_2019_v2 with corrected 902.02.03 table chunks.

Problems fixed
--------------
1. Table 902.02.03-2 ("Gyratory Compaction Effort") is a borderless table that
   pdfplumber missed entirely.  Insert a clean markdown chunk with embeddings.

2. Table 902.02.03-3 ("HMA Requirements for Design") was extracted by pdfplumber
   but multi-line column headers collapsed into garbled cells.  The L/M rows look
   identical, causing LLM confusion.  Replace the pdfplumber chunk with a clean
   version that has proper column labels and explicit Compaction Level rows.

3. Add a supplemental text chunk focusing on the 95.0–97.0% verification density
   from footnote 2 of Table 902.02.03-3 so Q47-style queries rank it directly.

4. Reformat the inline Table 902.02.02-1 ("Recycled Materials") which is currently
   stored as free text (making the LLM mis-read the 35% total vs. 25% RAP limit).

Usage
-----
    python scripts/fix_902_tables.py [--collection specs_2019_v2] [--dry-run]

    --collection  Target collection (default: specs_2019_v2).
    --dry-run     Print what would be inserted/deleted without touching the DB.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── path shim ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config   import config
from app.database import get_db
import openai


# ── embed helper ──────────────────────────────────────────────────────────

_oai = openai.OpenAI(api_key=config.OPENAI_API_KEY)

def _embed(text: str) -> list[float]:
    resp = _oai.embeddings.create(model=config.EMBEDDING_MODEL, input=[text])
    return resp.data[0].embedding


# ── chunk definitions ─────────────────────────────────────────────────────

def _table_902_02_03_2() -> dict[str, Any]:
    """
    Table 902.02.03-2: Gyratory Compaction Effort for HMA Mixtures.
    Defines the two compaction levels (L and M) with their ESAL thresholds
    and design/maximum gyration counts.
    Previously ABSENT from specs_2019_v2 (borderless table, pdfplumber missed it).
    """
    content = """\
Table 902.02.03-2 Gyratory Compaction Effort for HMA Mixtures

| Compaction Level | ESALs (millions) | N_des | N_max |
|---|---|---|---|
| L | < 0.3 | 50 | 75 |
| M | ≥ 0.3 | 75 | 115 |

Footnote 1: Design ESALs (Equivalent 80 kN Single-Axle Loads) refer to the \
anticipated traffic level expected on the design lane over a 20-year period.\
"""
    return {
        "content":  content,
        "metadata": {
            "doc":           "Spec2019",
            "kind":          "table",
            "division":      "MATERIALS",
            "page_pdf":      406,
            "page_printed":  406,
            "section_id":    "902.02.03",
            "section_title": "Mix Design",
            "table_id":      "902.02.03-2",
            "table_type":    "simple",
            "footnotes": [
                "Design ESALs (Equivalent 80 kN Single-Axle Loads) refer to the "
                "anticipated traffic level expected on the design lane over a 20-year period."
            ],
            "_patch": "fix_902_tables.py v1 – inserted missing borderless table",
        },
    }


def _table_902_02_03_3_clean() -> dict[str, Any]:
    """
    Table 902.02.03-3: HMA Requirements for Design (CLEAN replacement).
    The pdfplumber version collapsed multi-line column headers, making rows
    ambiguous (both L and M look identical).  This version has:
    - Explicit 'Compaction Level' column as the first column
    - Clear L vs M rows
    - All footnotes preserved
    """
    content = """\
Table 902.02.03-3 HMA Requirements for Design

| Compaction Level | Required Density @Ndes (%Gmm) | Required Density @Nmax (%Gmm) | VMA 37.5mm min% | VMA 25.0mm min% | VMA 19.0mm min% | VMA 12.5mm min% | VMA 9.5mm min% | VMA 4.75mm min% | VFA (%) | Dust-to-Binder Ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| L | 96.0 | ≤ 98.0 | 11.0 | 12.0 | 13.0 | 14.0 | 15.0 | 16.0 | 70 – 80 | 0.6 – 1.2 |
| M | 96.0 | ≤ 98.0 | 11.0 | 12.0 | 13.0 | 14.0 | 15.0 | 16.0 | 65 – 78 | 0.6 – 1.2 |

Footnote 1: For 37.5 mm nominal maximum size mixtures, the specified lower limit \
of the VFA is 64 percent for all design traffic levels.
Footnote 2: Required density is determined from maximum specific gravity (AASHTO T 209) \
and bulk specific gravity (AASHTO T 166). For verification, specimens must be between \
95.0 and 97.0 percent of maximum specific gravity at N_des.\
"""
    return {
        "content":  content,
        "metadata": {
            "doc":           "Spec2019",
            "kind":          "table",
            "division":      "MATERIALS",
            "page_pdf":      407,
            "page_printed":  407,
            "section_id":    "902.02.03",
            "section_title": "Mix Design",
            "table_id":      "902.02.03-3",
            "table_type":    "multi_header",
            "footnotes": [
                "For 37.5 mm nominal maximum size mixtures, the specified lower limit of "
                "the VFA is 64 percent for all design traffic levels.",
                "Required density is determined from maximum specific gravity (AASHTO T 209) "
                "and bulk specific gravity (AASHTO T 166). For verification, specimens must "
                "be between 95.0 and 97.0 percent of maximum specific gravity at N_des.",
            ],
            "_patch": "fix_902_tables.py v1 – replaced garbled pdfplumber extraction",
        },
    }


def _verification_density_text() -> dict[str, Any]:
    """
    Supplemental text chunk: verification density range.
    Targets Q47-style queries ("density requirement verification specimens N_des").
    The answer (95.0–97.0%) is in Table 902.02.03-3 footnote 2 but ranks too low
    because the table embedding is diluted by six aggregate-size columns.
    This standalone chunk gives the BM25 + vector retrieval a direct hit.
    """
    content = """\
902.02.03 Mix Design – Verification Density Requirement

For acceptance testing, the ME compacts HMA to the design gyrations (N_des) \
specified in Table 902.02.03-2 (Level L: N_des = 50; Level M: N_des = 75), \
using equipment per AASHTO T 312.

Verification: Compacted specimens used to verify the mix design must achieve \
between 95.0 and 97.0 percent of the maximum specific gravity at N_des. \
Maximum specific gravity is determined per AASHTO T 209; bulk specific gravity \
per AASHTO T 166. (Table 902.02.03-3, Footnote 2)\
"""
    return {
        "content":  content,
        "metadata": {
            "doc":           "Spec2019",
            "kind":          "text",
            "division":      "MATERIALS",
            "page_pdf":      407,
            "page_printed":  407,
            "section_id":    "902.02.03",
            "section_title": "Mix Design",
            "_patch": "fix_902_tables.py v1 – supplemental verification density chunk",
        },
    }


def _table_902_02_02_1_clean() -> dict[str, Any]:
    """
    Table 902.02.02-1: Use of Recycled Materials in HMA Base or Intermediate Course.
    Currently stored as free-text lines ("RAP 25", "CRCG 10", …).
    The LLM sometimes reads the surrounding "up to 35 percent of recycled materials"
    prose and answers '35%' instead of the specific RAP limit (25%).
    This clean chunk adds the proper markdown table + explicit prose clarification.
    """
    content = """\
Table 902.02.02-1 Use of Recycled Materials in HMA Base or Intermediate Course

The total recycled materials content may be up to 35 percent, with the following \
individual maximum limits by weight of total mixture:

| Recycled Material | Maximum Percentage (by weight) |
|---|---|
| RAP (Reclaimed Asphalt Pavement) | 25% |
| CRCG (Crushed Recycled Container Glass) | 10% |
| GBSM (Ground Bituminous Shingle Material) | 5% |
| RPCSA (Recycled Portland Cement Stabilized Aggregate) | 20% |

Note: The 35% total limit applies to the combined recycled materials content. \
The individual limits above must each be met separately. For HMA surface course, \
RAP is limited to 15 percent.\
"""
    return {
        "content":  content,
        "metadata": {
            "doc":           "Spec2019",
            "kind":          "table",
            "division":      "MATERIALS",
            "page_pdf":      405,
            "page_printed":  405,
            "section_id":    "902.02.02",
            "section_title": "Composition of Mixtures",
            "table_id":      "902.02.02-1",
            "table_type":    "simple",
            "footnotes": [],
            "_patch": "fix_902_tables.py v1 – clean recycled materials table",
        },
    }


# ── DB helpers ────────────────────────────────────────────────────────────

def _find_garbled_903_3_id(db: Any, collection: str) -> list[str]:
    """Return IDs of the pdfplumber-extracted Table 902.02.03-3 chunk(s)."""
    res = (
        db.table("chunks")
        .select("id,metadata")
        .eq("collection", collection)
        .eq("metadata->>section_id", "902.02.03")
        .eq("metadata->>kind", "table")
        .execute()
    )
    ids = []
    for row in res.data:
        tid = row["metadata"].get("table_id", "")
        patch = row["metadata"].get("_patch", "")
        if tid == "902.02.03-3" and "fix_902" not in patch:
            ids.append(row["id"])
    return ids


def _chunk_exists(db: Any, collection: str, table_id: str) -> bool:
    """Check whether a patched chunk already exists for this table_id."""
    res = (
        db.table("chunks")
        .select("id")
        .eq("collection", collection)
        .eq("metadata->>table_id", table_id)
        .like("metadata->>'_patch'", "fix_902%")
        .execute()
    )
    return len(res.data) > 0


def _insert_chunk(
    db:         Any,
    collection: str,
    chunk:      dict[str, Any],
    dry_run:    bool,
) -> None:
    content  = chunk["content"]
    metadata = chunk["metadata"]
    label    = metadata.get("table_id") or metadata.get("section_id")

    if dry_run:
        print(f"  [DRY-RUN] Would insert chunk: {label!r}")
        print(f"    content[:80]: {content[:80]!r}")
        return

    print(f"  Embedding chunk: {label!r} …", end="", flush=True)
    embedding = _embed(content)
    print(" done.")

    db.table("chunks").insert({
        "collection": collection,
        "content":    content,
        "metadata":   metadata,
        "embedding":  embedding,
    }).execute()
    print(f"  ✅ Inserted: {label!r}")


def _delete_chunks(
    db:         Any,
    ids:        list[str],
    label:      str,
    dry_run:    bool,
) -> None:
    if not ids:
        return
    if dry_run:
        print(f"  [DRY-RUN] Would delete {len(ids)} old chunk(s) for {label!r}: {ids}")
        return
    for cid in ids:
        db.table("chunks").delete().eq("id", cid).execute()
    print(f"  🗑️  Deleted {len(ids)} old chunk(s) for {label!r}")


# ── main ──────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", default="specs_2019_v2",
                        help="Target Supabase collection (default: specs_2019_v2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned changes without executing them")
    args = parser.parse_args()

    col     = args.collection
    dry_run = args.dry_run

    db = get_db()
    print(f"\n🔧 fix_902_tables.py — collection={col!r}  dry_run={dry_run}\n")

    # ── Step 1: Insert Table 902.02.03-2 (missing entirely) ────────────────
    print("Step 1: Table 902.02.03-2 (Gyratory Compaction Effort)")
    if _chunk_exists(db, col, "902.02.03-2"):
        print("  ⏭️  Already patched — skipping.")
    else:
        _insert_chunk(db, col, _table_902_02_03_2(), dry_run)

    # ── Step 2: Replace garbled Table 902.02.03-3 ──────────────────────────
    print("\nStep 2: Table 902.02.03-3 (HMA Requirements for Design — clean version)")
    if _chunk_exists(db, col, "902.02.03-3"):
        print("  ⏭️  Clean version already patched — skipping.")
    else:
        old_ids = _find_garbled_903_3_id(db, col)
        if old_ids:
            _delete_chunks(db, old_ids, "902.02.03-3 (garbled)", dry_run)
        else:
            print("  ℹ️  No existing pdfplumber chunk found to replace.")
        _insert_chunk(db, col, _table_902_02_03_3_clean(), dry_run)

    # ── Step 3: Supplemental verification density text chunk ───────────────
    print("\nStep 3: Supplemental verification density text (95.0–97.0%)")
    # Check by _patch key, not table_id
    res = (
        db.table("chunks")
        .select("id")
        .eq("collection", col)
        .eq("metadata->>section_id", "902.02.03")
        .like("metadata->>'_patch'", "fix_902%supplemental%")
        .execute()
    )
    if res.data:
        print("  ⏭️  Supplemental chunk already exists — skipping.")
    else:
        chunk = _verification_density_text()
        # Mark it distinctly
        chunk["metadata"]["_patch"] = "fix_902_tables.py v1 – supplemental verification density chunk"
        _insert_chunk(db, col, chunk, dry_run)

    # ── Step 4: Clean Table 902.02.02-1 (recycled materials) ───────────────
    print("\nStep 4: Table 902.02.02-1 (Recycled Materials — clean markdown)")
    if _chunk_exists(db, col, "902.02.02-1"):
        print("  ⏭️  Already patched — skipping.")
    else:
        _insert_chunk(db, col, _table_902_02_02_1_clean(), dry_run)

    print("\n✅ Done.\n")


if __name__ == "__main__":
    main()
