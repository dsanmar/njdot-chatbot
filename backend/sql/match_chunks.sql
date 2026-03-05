-- match_chunks: cosine-similarity vector search over the chunks table.
--
-- Changes vs. previous version:
--   • Added `collection text` to the RETURNS TABLE clause.
--   • Added `chunks.collection` to the SELECT list.
--
-- Run once in the Supabase SQL editor to replace the existing function.

create or replace function match_chunks(
  query_embedding   vector(1536),
  match_count       int      default 10,
  filter_collection text     default null,
  match_threshold   float8   default 0.0
)
returns table (
  id          uuid,
  content     text,
  metadata    jsonb,
  similarity  float8,
  collection  text          -- ← added
)
language sql stable
as $$
  select
    chunks.id,
    chunks.content,
    chunks.metadata,
    1 - (chunks.embedding <=> query_embedding) as similarity,
    chunks.collection                           -- ← added
  from chunks
  where
    (filter_collection is null or chunks.collection = filter_collection)
    and 1 - (chunks.embedding <=> query_embedding) > match_threshold
  order by chunks.embedding <=> query_embedding
  limit match_count;
$$;
