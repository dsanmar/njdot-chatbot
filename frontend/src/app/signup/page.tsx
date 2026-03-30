import type { Metadata } from 'next'
import SignupForm from '@/components/auth/SignupForm'

export const metadata: Metadata = {
  title: 'Create Account — NJDOT Spec Assistant',
}

export default function SignupPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F5F5F5] px-4 py-12">
      <SignupForm />
    </main>
  )
}
