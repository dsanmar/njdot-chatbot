import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#003366] px-6 text-white">
      {/* ── Logo band ── */}
      <div className="mb-8 text-center">
        <span className="inline-block rounded-sm bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-white/70">
          New Jersey Department of Transportation
        </span>
      </div>

      {/* ── Hero ── */}
      <div className="max-w-2xl text-center">
        <h1 className="mb-5 text-5xl font-bold tracking-tight leading-tight">
          NJDOT AI Assistant
        </h1>

        <p className="mb-10 text-lg leading-relaxed text-white/70">
          Get instant answers from NJDOT Standard Specifications, Material
          Procedures, and Construction Scheduling Manual
        </p>

        <Link
          href="/chat"
          className="inline-block rounded-lg bg-white px-8 py-3.5 text-base font-semibold text-[#003366] shadow-lg transition-colors hover:bg-white/90 focus:outline-none focus:ring-2 focus:ring-white/50"
        >
          Launch Chatbot
        </Link>
      </div>

      {/* ── Footer note ── */}
      <p className="mt-16 text-xs text-white/30">
      </p>
    </main>
  )
}
