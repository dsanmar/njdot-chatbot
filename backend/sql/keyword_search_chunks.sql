-- keyword_search_chunks: BM25-style full-text search over the chunks table.
--
-- Uses PostgreSQL's ts_rank_cd (cover-density ranking) which closely
-- approximates BM25 relevance scoring.
--
-- websearch_to_tsquery (Postgres ≥ 11) is used so that:
--   • Multi-word queries are handled naturally ("proposal bond" → AND)
--   • Quoted phrases work:  "421.03 materials"
--   • Negation works:       bond -performance
--
-- Run once in the Supabase SQL editor before using KeywordSearcher.

-- Step 1: GIN index for fast tsvector lookups (skip if it already exists).
create index if not exists chunks_content_fts
  on chunks
  using gin(to_tsvector('english', content));

-- Step 2: Create/replace the RPC function.
create or replace function keyword_search_chunks(
  search_query      text,
  match_count       int  default 10,
  filter_collection text default null
)
returns table (
  id          uuid,
  content     text,
  metadata    jsonb,
  rank        float8,
  collection  text
)
language sql stable
as $$
  select
    chunks.id,
    chunks.content,
    chunks.metadata,
    ts_rank_cd(
      to_tsvector('english', chunks.content),
      websearch_to_tsquery('english', search_query)
    )::float8 as rank,
    chunks.collection
  from chunks
  where
    (filter_collection is null or chunks.collection = filter_collection)
    and to_tsvector('english', chunks.content)
          @@ websearch_to_tsquery('english', search_query)
  order by rank desc
  limit match_count;
$$;
