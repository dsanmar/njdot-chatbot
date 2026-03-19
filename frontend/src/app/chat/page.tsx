import type { Metadata } from 'next'
import { createClient } from '@/lib/supabase/server'
import ChatInterface from '@/components/chat/ChatInterface'

export const metadata: Metadata = {
  title: 'Chat — NJDOT AI Assistant',
}

export default async function ChatPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  return <ChatInterface userEmail={user?.email} />
}
