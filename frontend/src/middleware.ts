/**
 * Supabase auth middleware for Next.js App Router.
 *
 * Responsibilities:
 *  1. Refresh the Supabase session on every request so cookies stay valid.
 *  2. Protect /chat — redirect unauthenticated visitors to /login.
 *  3. Redirect authenticated visitors away from /login and /signup to /chat.
 */
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  // Start with a pass-through response; the cookie setter below may replace it.
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          // Write updated auth cookies back to both the request and response
          // so the session is available downstream within the same cycle.
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          )
        },
      },
    },
  )

  // IMPORTANT: always use getUser() here — getSession() is not safe in
  // middleware because the session can come from an untrusted cookie.
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const { pathname } = request.nextUrl

  // ── Protect /chat ────────────────────────────────────────────────────────
  if (pathname.startsWith('/chat') && !user) {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = '/login'
    return NextResponse.redirect(loginUrl)
  }

  // ── Redirect authenticated users away from auth pages ────────────────────
  if ((pathname === '/login' || pathname === '/signup') && user) {
    const chatUrl = request.nextUrl.clone()
    chatUrl.pathname = '/chat'
    return NextResponse.redirect(chatUrl)
  }

  return supabaseResponse
}

export const config = {
  matcher: [
    /*
     * Run on all routes except:
     *  - _next/static  (static assets)
     *  - _next/image   (image optimisation)
     *  - favicon.ico
     *  - public files with extensions
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
