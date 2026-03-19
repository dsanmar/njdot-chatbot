'use client'

import { KeyboardEvent, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { askQuestion } from '@/lib/api'
import { createClient } from '@/lib/supabase/client'
import type { CitationItem } from '@/lib/types'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: CitationItem[]
  query_type?: string
  response_time_ms?: number
  isError?: boolean
}

interface ChatInterfaceProps {
  userEmail?: string
}

// ── Constants ─────────────────────────────────────────────────────────────────

const COLLECTIONS = [
  { label: 'All Documents',           value: '' },
  { label: 'Standard Specifications', value: 'specs_2019' },
  { label: 'Material Procedures',     value: 'material_procs' },
  { label: 'Construction Scheduling', value: 'scheduling' },
] as const

// ── Component ─────────────────────────────────────────────────────────────────

export default function ChatInterface({ userEmail }: ChatInterfaceProps) {
  const [messages, setMessages]     = useState<Message[]>([])
  const [input, setInput]           = useState('')
  const [collection, setCollection] = useState('')
  const [isLoading, setIsLoading]   = useState(false)
  const messagesEndRef              = useRef<HTMLDivElement>(null)
  const router                      = useRouter()

  // The most recent non-error assistant message drives the citations panel
  const latestAnswer = [...messages]
    .reverse()
    .find((m) => m.role === 'assistant' && !m.isError)

  // Auto-scroll to bottom whenever messages or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleSend = async () => {
    const query = input.trim()
    if (!query || isLoading) return

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: query }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const data = await askQuestion(query, collection || undefined)
      const assistantMsg: Message = {
        id:               crypto.randomUUID(),
        role:             'assistant',
        content:          data.answer,
        citations:        data.citations,
        query_type:       data.query_type,
        response_time_ms: data.response_time_ms,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg: Message = {
        id:      crypto.randomUUID(),
        role:    'assistant',
        content: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
        isError: true,
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSignOut = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/')
    router.refresh()
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen flex-col bg-white">

      {/* ── Header ── */}
      <header className="flex shrink-0 items-center justify-between bg-[#003366] px-4 py-3 shadow-md">
        {/* Left: back + title */}
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="text-sm text-white/60 transition-colors hover:text-white"
          >
            ← Back
          </Link>
          <span className="h-4 w-px bg-white/20" />
          <span className="font-semibold text-white">NJDOT AI Assistant</span>
        </div>

        {/* Right: user email + sign out */}
        <div className="flex items-center gap-3">
          {userEmail && (
            <>
              <span className="hidden text-xs text-white/50 sm:block">
                {userEmail}
              </span>
              <span className="hidden h-3 w-px bg-white/20 sm:block" />
            </>
          )}
          <button
            onClick={handleSignOut}
            className="rounded-md px-2.5 py-1 text-xs text-white/70 transition-colors hover:bg-white/10 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* ── Body: two-column ── */}
      <div className="flex min-h-0 flex-1">

        {/* ── Left: chat (full width on mobile, 60% on md+) ── */}
        <div className="flex min-w-0 flex-1 flex-col md:w-3/5 md:flex-none">

          {/* Message list */}
          <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4">
            {messages.length === 0 && !isLoading && (
              <div className="flex h-full items-center justify-center">
                <p className="text-sm text-gray-400">
                  Ask a question about NJDOT specifications, procedures, or scheduling.
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'user' ? (
                  /* User bubble */
                  <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-[#003366] px-4 py-2.5 text-sm text-white shadow-sm">
                    {msg.content}
                  </div>
                ) : (
                  /* Assistant reply */
                  <div className="max-w-[88%]">
                    <p
                      className={`text-sm leading-relaxed whitespace-pre-wrap ${
                        msg.isError ? 'text-red-600' : 'text-gray-800'
                      }`}
                    >
                      {msg.content}
                    </p>
                    {msg.response_time_ms != null && (
                      <p className="mt-1.5 text-xs text-gray-400">
                        {msg.query_type} · {msg.response_time_ms} ms
                        {msg.citations && msg.citations.length > 0 && (
                          <> · {msg.citations.length} source{msg.citations.length > 1 ? 's' : ''}</>
                        )}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-2.5">
                  <span
                    className="h-2 w-2 rounded-full bg-gray-400 animate-pulse"
                    style={{ animationDelay: '0ms' }}
                  />
                  <span
                    className="h-2 w-2 rounded-full bg-gray-400 animate-pulse"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="h-2 w-2 rounded-full bg-gray-400 animate-pulse"
                    style={{ animationDelay: '300ms' }}
                  />
                  <span className="ml-1 text-xs text-gray-500">Thinking…</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ── Input bar ── */}
          <div className="shrink-0 border-t bg-white px-4 py-3">
            {/* Source filter */}
            <div className="mb-2">
              <select
                value={collection}
                onChange={(e) => setCollection(e.target.value)}
                className="rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-600 focus:border-[#003366] focus:outline-none focus:ring-1 focus:ring-[#003366]/20"
              >
                {COLLECTIONS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Text input + send */}
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about specifications, procedures, or scheduling…"
                disabled={isLoading}
                className="flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-[#003366] focus:outline-none focus:ring-2 focus:ring-[#003366]/10 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400"
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="rounded-lg bg-[#003366] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#002244] focus:outline-none focus:ring-2 focus:ring-[#003366]/40 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* ── Right: Citations panel (hidden on mobile, 40% on md+) ── */}
        <aside className="hidden md:flex md:w-2/5 flex-col border-l bg-gray-50">
          {/* Panel header */}
          <div className="shrink-0 border-b bg-white px-4 py-3">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-700">
              Sources
              {latestAnswer?.citations && latestAnswer.citations.length > 0 && (
                <span className="rounded-full bg-[#003366] px-2 py-0.5 text-xs font-medium text-white">
                  {latestAnswer.citations.length}
                </span>
              )}
            </h2>
          </div>

          {/* Citation cards */}
          <div className="flex-1 overflow-y-auto p-4">
            {!latestAnswer?.citations || latestAnswer.citations.length === 0 ? (
              <p className="text-sm text-gray-400">
                Source citations will appear here after your first question.
              </p>
            ) : (
              <div className="space-y-3">
                {latestAnswer.citations.map((cit, i) => (
                  <CitationCard key={cit.chunk_id || i} citation={cit} index={i} />
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}

// ── Citation card sub-component ───────────────────────────────────────────────

function CitationCard({ citation, index }: { citation: CitationItem; index: number }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3.5 shadow-sm">
      {/* Row 1: document name + page */}
      <div className="mb-1 flex items-start justify-between gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[#003366]">
          {citation.document || 'NJDOT Document'}
        </span>
        <span className="shrink-0 text-xs text-gray-400">p.{citation.page_printed}</span>
      </div>

      {/* Row 2: section */}
      <p className="text-sm font-medium text-gray-800 leading-snug">{citation.section}</p>

      {/* Row 3: pdf page + link placeholder */}
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-gray-400">PDF p.{citation.page_pdf}</span>
        {/* placeholder — will link to actual PDF viewer later */}
        <button
          type="button"
          onClick={() => alert(`PDF viewer coming soon.\nChunk ID: ${citation.chunk_id}`)}
          className="text-xs text-[#003366] hover:underline"
        >
          View PDF →
        </button>
      </div>
    </div>
  )
}
