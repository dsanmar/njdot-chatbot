"""Revert Q97 ceiling chunk from v2 back to v1 wording."""
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

# ── Find the chunk ────────────────────────────────────────────────────────
res = db.table("chunks").select("id,metadata") \
    .eq("collection", COLLECTION) \
    .eq("metadata->>section_id", "902.02.02") \
    .execute()

target = None
for row in res.data:
    patch = (row["metadata"] or {}).get("_patch", "")
    if "combined recycled materials ceiling" in patch:
        target = row
        break

if not target:
    print("❌  Ceiling chunk not found.")
    sys.exit(1)

print(f"Found chunk id={target['id']}")

# ── v1 content (the version that gave 91% — doesn't fix Q97 but causes  ──
# ── no collateral regressions) ───────────────────────────────────────────
V1_CONTENT = """\
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

print("Embedding v1 content …", end="", flush=True)
resp = oai.embeddings.create(model=config.EMBEDDING_MODEL, input=[V1_CONTENT])
print(" done.")

db.table("chunks").update({
    "content":   V1_CONTENT,
    "embedding": resp.data[0].embedding,
    "metadata":  {
        **target["metadata"],
        "_patch": "fix_q21_q97.py v1 – combined recycled materials ceiling chunk (reverted from v2)",
    },
}).eq("id", target["id"]).execute()

print("✅  Reverted to v1 content.")
