"""Re-ingest Section 902.02.03 as clean markdown.

Steps
-----
1. Delete all chunks where metadata->>'section_id' = '902.02.03'
   and collection = 'specs_2019'.
2. Build one clean chunk with pipe-delimited markdown tables and explicit
   column headers so the LLM can read VMA / VFA values without ambiguity.
3. Embed via embed_chunks() (text-embedding-3-small, 1536 dims).
4. Insert the new row into the chunks table with corrected metadata
   (page_pdf=441, page_printed=407).

Usage
-----
    # From backend/ directory:
    python scripts/fix_table_902.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# ── Ensure backend/ package root is on sys.path ──────────────────────────────
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.config             import config
from app.database           import get_db
from app.ingestion.embedder import embed_chunks


# ── Target metadata ───────────────────────────────────────────────────────────

_COLLECTION  = "specs_2019"
_SECTION_ID  = "902.02.03"
_METADATA: Dict[str, Any] = {
    "doc":           "Spec2019",
    "section_id":    "902.02.03",
    "section_title": "Mix Design",
    "division":      "DIVISION 900 – HOT MIX ASPHALT",
    "page_pdf":      441,
    "page_printed":  407,
    "kind":          "text",
}

# ── Clean chunk content ───────────────────────────────────────────────────────
# Tables are pipe-delimited markdown with explicit column headers so the LLM
# can unambiguously associate every value with its column.

_CONTENT = """\
SECTION 902 – HOT MIX ASPHALT MATERIALS
902.02.03 Mix Design

Table 902.02.03-2 Gyratory Compaction Effort for HMA Mixtures

| Compaction Level | ESALs (millions) | N_des | N_max |
|---|---|---|---|
| L | < 0.3 | 50 | 75 |
| M | ≥ 0.3 | 75 | 115 |

Footnote 1: Design ESALs (Equivalent 80kN Single-Axle Loads) refer to anticipated traffic level on the design lane over a 20 year period.

Table 902.02.03-3 HMA Requirements for Design

| Compaction Level | @Ndes (%Gmm) | @Nmax (%Gmm) | VMA 37.5mm (min%) | VMA 25.0mm (min%) | VMA 19.0mm (min%) | VMA 12.5mm (min%) | VMA 9.5mm (min%) | VMA 4.75mm (min%) | VFA (%) | Dust-to-Binder Ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| L | 96.0 | ≤98.0 | 11.0 | 12.0 | 13.0 | 14.0 | 15.0 | 16.0 | 70-80 | 0.6-1.2 |
| M | 96.0 | ≤98.0 | 11.0 | 12.0 | 13.0 | 14.0 | 15.0 | 16.0 | 65-78 | 0.6-1.2 |

Footnote 1: For 37.5 mm nominal maximum size mixtures, the specified lower limit of the VFA is 64 percent for all design traffic levels.
Footnote 2: Maximum specific gravity determined per AASHTO T 209. Bulk specific gravity per AASHTO T 166. Verification specimens must be between 95.0 and 97.0 percent of maximum specific gravity at N_des.

For mix designs including RAP or GBSM, report: percentage of RAP or GBSM, percentage of asphalt binder in RAP or GBSM, percentage of new asphalt binder, total percentage of asphalt binder, and percentage of each type of virgin aggregate.
Tensile strength ratio minimum is 80 percent when tested per AASHTO T 283.\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _delete_existing(db: Any) -> int:
    """
    Delete all chunks where section_id = '902.02.03' AND collection = 'specs_2019'.

    Uses the PostgREST JSON containment filter (@>) which is the only reliable
    JSONB filter exposed by the supabase-py client.

    Returns the number of rows deleted (may be 0 on a fresh database).
    """
    resp = (
        db.table("chunks")
          .delete()
          .contains("metadata", {"section_id": _SECTION_ID})
          .eq("collection", _COLLECTION)
          .execute()
    )
    deleted = resp.data if resp.data else []
    return len(deleted)


def _build_chunk() -> List[Dict[str, Any]]:
    """Return a single-element list in the shape embed_chunks() expects."""
    return [
        {
            "content":  _CONTENT,
            "metadata": _METADATA,
        }
    ]


def _insert_chunk(db: Any, chunk: Dict[str, Any]) -> str:
    """Insert one embedded chunk and return the new row's UUID."""
    row = {
        "content":    chunk["content"],
        "embedding":  chunk["embedding"],
        "metadata":   chunk["metadata"],
        "collection": _COLLECTION,
    }
    resp = db.table("chunks").insert(row).execute()
    return resp.data[0]["id"]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not config.validate():
        sys.exit(1)

    db = get_db()

    # ── Step 1: Delete existing 902.02.03 chunks ──────────────────────────────
    print(f"\nDeleting chunks where section_id='{_SECTION_ID}' "
          f"and collection='{_COLLECTION}'…")
    n_deleted = _delete_existing(db)
    print(f"  Deleted: {n_deleted} chunk(s)")

    # ── Step 2: Build chunk dict ───────────────────────────────────────────────
    chunks = _build_chunk()
    print(f"\nEmbedding {len(chunks)} new chunk(s)…")

    # ── Step 3: Embed ─────────────────────────────────────────────────────────
    embed_chunks(chunks)

    # ── Step 4: Insert ────────────────────────────────────────────────────────
    new_id = _insert_chunk(db, chunks[0])
    print(f"  New chunk ID : {new_id}")
    print(f"  section_id   : {_METADATA['section_id']}")
    print(f"  page_printed : {_METADATA['page_printed']}")
    print(f"  page_pdf     : {_METADATA['page_pdf']}")
    print(f"  content length: {len(_CONTENT)} chars")
    print("\n✅ fix_table_902.py complete.\n")


if __name__ == "__main__":
    main()
