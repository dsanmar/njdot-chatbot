"""Inspect 902.02.x chunks in specs_2019_v2 and get a good metadata sample."""
from dotenv import load_dotenv
load_dotenv("/Users/marsanto/DevProjects/njdot-chatbot/backend/.env")

from app.database import get_db

db = get_db()

# ── 1. All 902.02 chunks in v2 ─────────────────────────────────────────────
res = db.table("chunks").select("id,content,metadata,collection") \
    .eq("collection", "specs_2019_v2") \
    .like("metadata->>section_id", "902.02%") \
    .order("metadata->>section_id") \
    .execute()

print(f"=== 902.02.x chunks in specs_2019_v2 ({len(res.data)} total) ===\n")
for r in res.data:
    m = r["metadata"]
    print(f"section_id={m.get('section_id')!r:25}  kind={m.get('kind')!r:12}  "
          f"doc={m.get('doc')!r}  division={m.get('division')!r}")
    print(f"  content[:150]: {r['content'][:150]!r}")
    print()

# ── 2. Full metadata for the first table chunk (to see all fields) ─────────
print("\n=== Full metadata of first 'table' kind chunk ===")
for r in res.data:
    if r["metadata"].get("kind") == "table":
        import json
        print(json.dumps(r["metadata"], indent=2))
        break
