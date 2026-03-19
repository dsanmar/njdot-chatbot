export interface CitationItem {
  document: string
  section: string
  page_printed: number
  page_pdf: number
  chunk_id: string
}

export interface QueryResponse {
  answer: string
  citations: CitationItem[]
  query_type: string
  response_time_ms: number
}
