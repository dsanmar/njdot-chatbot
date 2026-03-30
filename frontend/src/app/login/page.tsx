import type { Metadata } from 'next'
import LoginForm from '@/components/auth/LoginForm'

export const metadata: Metadata = {
  title: 'Sign In — NJDOT Spec Assistant',
}

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F5F5F5] px-4 py-12">
      <LoginForm />
    </main>
  )
}
