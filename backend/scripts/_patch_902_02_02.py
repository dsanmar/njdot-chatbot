"""
Update the existing 902.02.02-1 patch chunk to make the
standard-HMA vs HIGH-RAP distinction explicit so the LLM
doesn't confuse the 25% MAX with the 30% MIN from Section 902.13.
"""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent / ".env")

import sys, openai
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config   import config
from app.database import get_db

db  = get_db()
oai = openai.OpenAI(api_key=config.OPENAI_API_KEY)

COLLECTION = "specs_2019_v2"

NEW_CONTENT = """\
Table 902.02.02-1 Use of Recycled Materials in HMA Base or Intermediate Course
(Section 902.02 — Standard HMA; this section does NOT apply to HMA HIGH RAP, Section 902.13)

For standard HMA base or intermediate course the total recycled materials content \
may not exceed 35 percent by weight of total mixture. Each recycled material is also \
subject to the following individual MAXIMUM limits:

| Recycled Material | Maximum Percentage (by weight) |
|---|---|
| RAP (Reclaimed Asphalt Pavement) | 25% |
| CRCG (Crushed Recycled Container Glass) | 10% |
| GBSM (Ground Bituminous Shingle Material) | 5% |
| RPCSA (Recycled Portland Cement Stabilized Aggregate) | 20% |

Important: The maximum RAP content for standard HMA base or intermediate course \
is 25 percent. (Section 902.13 HMA HIGH RAP has a different rule — it REQUIRES a \
minimum of 30 percent RAP; that minimum is separate from this maximum.)

For HMA surface course, RAP is limited to 15 percent maximum.\
"""

# ── Find the existing patch chunk ─────────────────────────────────────────
res = db.table("chunks").select("id,content,metadata") \
    .eq("collection", COLLECTION) \
    .eq("metadata->>table_id", "902.02.02-1") \
    .execute()

if not res.data:
    print("❌  Patch chunk for 902.02.02-1 not found — run fix_902_tables.py first.")
    sys.exit(1)

row = res.data[0]
print(f"Found patch chunk id={row['id']}")
print(f"Old content length: {len(row['content'])}")
print(f"New content length: {len(NEW_CONTENT)}")

# ── Re-embed ───────────────────────────────────────────────────────────────
print("Embedding …", end="", flush=True)
resp = oai.embeddings.create(model=config.EMBEDDING_MODEL, input=[NEW_CONTENT])
new_embedding = resp.data[0].embedding
print(" done.")

# ── Update the row ─────────────────────────────────────────────────────────
db.table("chunks").update({
    "content":   NEW_CONTENT,
    "embedding": new_embedding,
    "metadata":  {
        **row["metadata"],
        "_patch": "fix_902_tables.py v2 – added standard-HMA vs HIGH-RAP disambiguation",
    },
}).eq("id", row["id"]).execute()

print("✅  Updated 902.02.02-1 chunk with disambiguation note.")
