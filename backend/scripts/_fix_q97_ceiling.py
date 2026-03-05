"""
Re-word the Q97 combined ceiling chunk — remove the 'effectively 30 percent'
sentence that the LLM was anchoring on.
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

# ── Find the chunk by its _patch label ────────────────────────────────────
res = db.table("chunks").select("id,content,metadata") \
    .eq("collection", COLLECTION) \
    .eq("metadata->>section_id", "902.02.02") \
    .execute()

target = None
for row in res.data:
    if "combined recycled materials ceiling chunk" in (row["metadata"] or {}).get("_patch", ""):
        target = row
        break

if not target:
    print("❌  Ceiling chunk not found.")
    sys.exit(1)

print(f"Found chunk id={target['id']}")
print(f"Old content:\n{target['content']}\n")

# ── Rewritten content ─────────────────────────────────────────────────────
# Key change: remove "effectively 30 percent" entirely.
# State the 35% ceiling as the answer to "maximum combined", then list
# individual limits separately.  Make the ceiling the first and last thing.
NEW_CONTENT = """\
902.02.02 Combined Recycled Materials Ceiling — HMA Base or Intermediate Course

The combined total of all recycled materials in HMA base or intermediate course \
must not exceed 35 percent by weight of total mixture. This 35 percent is the \
maximum combined ceiling for RAP, CRCG, GBSM, RPCSA, and any mixture of them.

Individual maximum limits (from Table 902.02.02-1):
- RAP (Reclaimed Asphalt Pavement): 25 percent maximum
- CRCG (Crushed Recycled Container Glass): 10 percent maximum
- GBSM (Ground Bituminous Shingle Material): 5 percent maximum
- RPCSA (Recycled Portland Cement Stabilized Aggregate): 20 percent maximum

Both rules apply simultaneously: each material stays within its individual limit \
AND the combined total does not exceed 35 percent. For example, a mix using \
25 percent RAP and 5 percent GBSM totals 30 percent combined, which is within \
the 35 percent ceiling.\
"""

print(f"New content:\n{NEW_CONTENT}\n")

print("Embedding …", end="", flush=True)
resp = oai.embeddings.create(model=config.EMBEDDING_MODEL, input=[NEW_CONTENT])
new_embedding = resp.data[0].embedding
print(" done.")

db.table("chunks").update({
    "content":   NEW_CONTENT,
    "embedding": new_embedding,
    "metadata":  {
        **target["metadata"],
        "_patch": "fix_q21_q97.py v2 – combined recycled materials ceiling (35% first, no '30%' anchor)",
    },
}).eq("id", target["id"]).execute()

print("✅  Updated Q97 ceiling chunk.")
