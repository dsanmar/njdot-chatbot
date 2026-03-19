'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

export default function LoginForm() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    const supabase = createClient()
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (authError) {
      setError(authError.message)
      setIsLoading(false)
      return
    }

    router.push('/chat')
    router.refresh()
  }

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
          Sign in to your account
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
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
            {isLoading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-gray-500">
          Don&apos;t have an account?{' '}
          <Link
            href="/signup"
            className="font-medium text-[#003366] hover:underline"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
