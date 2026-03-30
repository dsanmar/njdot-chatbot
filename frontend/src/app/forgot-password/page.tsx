import type { Metadata } from 'next'
import ForgotPasswordForm from '@/components/auth/ForgotPasswordForm'

export const metadata: Metadata = {
  title: 'Reset Password — NJDOT Spec Assistant',
}

export default function ForgotPasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F5F5F5] px-4 py-12">
      <ForgotPasswordForm />
    </main>
  )
}
