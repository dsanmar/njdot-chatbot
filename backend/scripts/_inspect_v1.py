"""Pull v1 Table 902.02.03-2 content and 902.02.02 RAP details."""
from dotenv import load_dotenv
load_dotenv("/Users/marsanto/DevProjects/njdot-chatbot/backend/.env")

from app.database import get_db

db = get_db()

# ── Table 902.02.03-2 in v1 ───────────────────────────────────────────────
print("=== v1 Table 902.02.03-2 ===")
res = db.table("chunks").select("id,content,metadata") \
    .eq("collection", "specs_2019") \
    .like("content", "%902.02.03-2%") \
    .execute()
for r in res.data:
    print(f"kind={r['metadata'].get('kind')!r}  section_id={r['metadata'].get('section_id')!r}")
    print(r["content"])
    print()

# ── 902.02.02 composition in v2 (full content for RAP percentage) ─────────
print("\n=== v2 902.02.02 composition full ===")
res2 = db.table("chunks").select("id,content,metadata") \
    .eq("collection", "specs_2019_v2") \
    .eq("metadata->>section_id", "902.02.02") \
    .execute()
for r in res2.data:
    print(f"kind={r['metadata'].get('kind')!r}")
    print(r["content"])
    print()

# ── Q9 gold: "What is the max RAP content allowed by weight" ─────────────
# Search for "RAP" in 902.02 v2 content
print("\n=== v2 any 902.02 chunk mentioning RAP percentages ===")
res3 = db.table("chunks").select("id,content,metadata") \
    .eq("collection", "specs_2019_v2") \
    .like("metadata->>section_id", "902.02%") \
    .like("content", "%RAP%") \
    .execute()
for r in res3.data:
    m = r["metadata"]
    print(f"section_id={m.get('section_id')!r}  kind={m.get('kind')!r}")
    # Print all lines mentioning RAP or percentage
    for line in r["content"].split("\n"):
        if "RAP" in line or "%" in line or "percent" in line.lower():
            print(f"  {line}")
    print()
