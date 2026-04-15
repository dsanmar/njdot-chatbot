import type { QueryResponse } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/**
 * POST /api/query — run a RAG query against the NJDOT backend.
 *
 * @param query      Natural-language question.
 * @param collection Optional collection filter: "specs_2019_v2" | "material_procs" |
 *                   "scheduling".  Omit (or pass undefined) to search all.
 * @throws Error with the backend detail message on non-2xx responses.
 */
export async function askQuestion(
  query: string,
  collection?: string,
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/api/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      collection: collection ?? null,
    }),
  })

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // JSON parse failure — keep the generic message
    }
    throw new Error(detail)
  }

  return res.json() as Promise<QueryResponse>
}
