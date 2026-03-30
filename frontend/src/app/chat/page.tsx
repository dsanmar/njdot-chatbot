import type { Metadata } from 'next'
import { createClient } from '@/lib/supabase/server'
import ChatInterface from '@/components/chat/ChatInterface'

export const metadata: Metadata = {
  title: 'NJDOT - Smart Assistant',
}

export default async function ChatPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  return <ChatInterface userId={user?.id} userEmail={user?.email} />
}
