"""Confirm source text for Q21 (CRCG contamination) and Q97 (35% ceiling)."""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent / ".env")
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.database import get_db

db = get_db()

# ── Q21: CRCG contamination in 902.02.02 text chunks ─────────────────────
print("=== Q21 source: 902.02.02 text – all content ===\n")
res = db.table("chunks").select("id,content,metadata") \
    .eq("collection", "specs_2019_v2") \
    .eq("metadata->>section_id", "902.02.02") \
    .eq("metadata->>kind", "text") \
    .execute()
for r in res.data:
    print(r["content"])
    print()

# ── Q97: 35% ceiling – full 902.02.02-1 patch chunk ──────────────────────
print("\n=== Q97 source: current 902.02.02-1 patch chunk ===\n")
res2 = db.table("chunks").select("id,content,metadata") \
    .eq("collection", "specs_2019_v2") \
    .eq("metadata->>table_id", "902.02.02-1") \
    .execute()
for r in res2.data:
    print(f"[id={r['id']}]")
    print(r["content"])
    print()

# ── Check if any existing standalone contamination chunk ─────────────────
print("\n=== Existing patch chunks in 902.02.02 ===")
res3 = db.table("chunks").select("id,metadata") \
    .eq("collection", "specs_2019_v2") \
    .eq("metadata->>section_id", "902.02.02") \
    .execute()
for r in res3.data:
    m = r["metadata"]
    print(f"  id={r['id'][:8]}…  kind={m.get('kind')!r:<8}  "
          f"table_id={m.get('table_id')!r}  patch={bool(m.get('_patch'))}")
