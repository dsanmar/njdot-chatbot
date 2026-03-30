'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'

export default function ForgotPasswordForm() {
  const [email, setEmail]         = useState('')
  const [error, setError]         = useState<string | null>(null)
  const [success, setSuccess]     = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    const supabase = createClient()
    const { error: authError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/update-password`,
    })

    if (authError) {
      setError(authError.message)
      setIsLoading(false)
      return
    }

    setSuccess(true)
    setIsLoading(false)
  }

  // ── Success state — no logo, just icon + message ──────────────────────────
  if (success) {
    return (
      <div className="w-full" style={{ maxWidth: '480px' }}>
        <div className="rounded-2xl bg-white shadow-xl ring-1 ring-black/5" style={{ padding: '44px' }}>
          <Link href="/" className="mb-5 block text-[13px] text-gray-400 hover:text-gray-600">
            ← Back to home
          </Link>
          <div className="flex flex-col items-center text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-blue-50">
              <svg className="h-7 w-7 text-[#1B3A6B]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-bold text-[#1B3A6B]">Check your email</h2>
            <p className="text-sm text-gray-500">
              If an account exists for{' '}
              <span className="font-medium text-gray-700">{email}</span>,
              we sent a password reset link. Click it to set a new password.
            </p>
            <Link
              href="/login"
              className="mt-6 text-sm font-semibold text-[#1B3A6B] hover:underline"
            >
              ← Back to sign in
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // ── Form ─────────────────────────────────────────────────────────────────────
  return (
    <div className="w-full" style={{ maxWidth: '480px' }}>
      {/* Card */}
      <div className="rounded-2xl bg-white shadow-xl ring-1 ring-black/5" style={{ padding: '44px' }}>

        {/* Back to home — inside card, top */}
        <Link href="/" className="mb-5 block text-[13px] text-gray-400 hover:text-gray-600">
          ← Back to home
        </Link>

        {/* Logo */}
        <div className="mb-5 flex justify-center">
          <Image src="/njdot_logo.png" alt="NJDOT" width={64} height={64} priority />
        </div>

        <h1 className="mb-1 text-center text-xl font-bold text-[#1B3A6B]">Smart Assistant</h1>
        <p className="mb-6 text-center text-sm text-gray-400">Reset your password</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-gray-700">
              Email address
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              placeholder="you@example.com"
              style={{ height: '44px' }}
              className="w-full rounded-lg border border-[#E8E8E8] bg-[#F5F5F5] px-3 text-sm text-gray-800 placeholder:text-gray-400 transition-colors focus:border-[#1B3A6B] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#1B3A6B]/10 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-50 px-3 py-2.5 text-xs text-red-700 ring-1 ring-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            style={{ height: '44px' }}
            className="w-full rounded-lg bg-[#CC2529] text-sm font-semibold text-white transition-colors hover:bg-[#a81e21] focus:outline-none focus:ring-2 focus:ring-[#CC2529]/30 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? 'Sending…' : 'Send Reset Link'}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-gray-500">
          <Link href="/login" className="font-semibold text-[#1B3A6B] hover:underline">
            ← Back to sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
