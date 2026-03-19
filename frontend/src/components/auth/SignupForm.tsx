'use client'

import { useState } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'

export default function SignupForm() {
  const [email, setEmail]                   = useState('')
  const [password, setPassword]             = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError]                   = useState<string | null>(null)
  const [success, setSuccess]               = useState(false)
  const [isLoading, setIsLoading]           = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)

    // ── Client-side validation ────────────────────────────────────────────
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsLoading(true)

    const supabase = createClient()
    const { error: authError } = await supabase.auth.signUp({ email, password })

    if (authError) {
      setError(authError.message)
      setIsLoading(false)
      return
    }

    setSuccess(true)
  }

  // ── Success state ─────────────────────────────────────────────────────────
  if (success) {
    return (
      <div className="w-full max-w-sm text-center">
        <div className="rounded-t-xl bg-[#003366] px-6 py-5 text-center">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-white/60">
            New Jersey Department of Transportation
          </p>
          <h1 className="text-xl font-bold text-white">NJDOT AI Assistant</h1>
        </div>
        <div className="rounded-b-xl border border-t-0 border-gray-200 bg-white px-6 py-8 shadow-lg">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
            <svg
              className="h-6 w-6 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h2 className="mb-2 text-base font-semibold text-gray-800">
            Check your email
          </h2>
          <p className="text-sm text-gray-500">
            We sent a confirmation link to{' '}
            <span className="font-medium text-gray-700">{email}</span>. Click the
            link to activate your account, then{' '}
            <Link href="/login" className="font-medium text-[#003366] hover:underline">
              sign in
            </Link>
            .
          </p>
        </div>
      </div>
    )
  }

  // ── Signup form ───────────────────────────────────────────────────────────
  return (
    <div className="w-full max-w-sm">
      {/* ── NJDOT header band ── */}
      <div className="rounded-t-xl bg-[#003366] px-6 py-5 text-center">
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-white/60">
          New Jersey Department of Transportation
        </p>
        <h1 className="text-xl font-bold text-white">NJDOT AI Assistant</h1>
      </div>

      {/* ── Card body ── */}
      <div className="rounded-b-xl border border-t-0 border-gray-200 bg-white px-6 py-6 shadow-lg">
        <h2 className="mb-5 text-center text-sm font-semibold text-gray-700">
          Create your account
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-xs font-medium text-gray-600"
            >
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
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-[#003366] focus:outline-none focus:ring-2 focus:ring-[#003366]/10 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          {/* Password */}
          <div>
            <label
              htmlFor="password"
              className="mb-1.5 block text-xs font-medium text-gray-600"
            >
              Password{' '}
              <span className="font-normal text-gray-400">(min. 8 characters)</span>
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              placeholder="••••••••"
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-[#003366] focus:outline-none focus:ring-2 focus:ring-[#003366]/10 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          {/* Confirm password */}
          <div>
            <label
              htmlFor="confirm-password"
              className="mb-1.5 block text-xs font-medium text-gray-600"
            >
              Confirm password
            </label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isLoading}
              placeholder="••••••••"
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm text-gray-800 placeholder:text-gray-400 focus:border-[#003366] focus:outline-none focus:ring-2 focus:ring-[#003366]/10 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          {/* Error message */}
          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2.5 text-xs text-red-700">
              {error}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-[#003366] py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#002244] focus:outline-none focus:ring-2 focus:ring-[#003366]/40 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-gray-500">
          Already have an account?{' '}
          <Link
            href="/login"
            className="font-medium text-[#003366] hover:underline"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
