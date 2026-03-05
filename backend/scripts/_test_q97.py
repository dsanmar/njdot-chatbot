"""Quick single-question pipeline test for Q97."""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent / ".env")
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.retrieval.hybrid_ranker         import HybridRanker
from app.generation.prompt_builder       import PromptBuilder
from app.generation.llm_client           import LLMClient

COLLECTION = "specs_2019_v2"
QUERY = (
    "A contractor wants to use RAP in an HMA base course and also include GBSM. "
    "What is the maximum combined percentage of these two recycled materials, "
    "and what are their individual limits?"
)
GOLD = (
    "The total recycled materials in HMA base or intermediate course cannot exceed "
    "35 percent. RAP individually is limited to 25 percent maximum, and GBSM is "
    "limited to 5 percent maximum. Together they may not exceed the 35 percent "
    "combined ceiling (Table 902.02.02-1)."
)

print(f"Query: {QUERY}\n")

hybrid = HybridRanker()
chunks = hybrid.search(QUERY, collection=COLLECTION, match_count=10)

print(f"Top retrieved chunks ({len(chunks)}):")
for i, c in enumerate(chunks, 1):
    m   = c.get("metadata", {})
    tid = m.get("table_id", "")
    pat = "🔧" if m.get("_patch") else ""
    rrf = c.get("rrf_score", c.get("similarity", 0))
    print(f"  #{i:02d}  sec={m.get('section_id'):<22} kind={m.get('kind'):<8} "
          f"{('['+tid+']') if tid else '':<18}{pat}  score={rrf:.4f}")

builder = PromptBuilder()
prompt  = builder.build(QUERY, chunks)

llm    = LLMClient()
answer = llm.complete(prompt)

print(f"\nSystem answer: {answer}")
print(f"Gold answer:   {GOLD}")
print(f"\n{'✅  PASS' if '35' in answer else '❌  FAIL — 35% not in answer'}")
