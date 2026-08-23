import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * Server-side Supabase client for use in Server Components / Route Handlers / Server
 * Actions. `cookies()` is async as of Next.js 15+. The `setAll` no-op guard matters when
 * this is called from a Server Component render, where Next.js forbids writing cookies
 * (only Server Actions/Route Handlers may); `middleware.ts` is what actually refreshes the
 * session cookie.
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            for (const { name, value, options } of cookiesToSet) {
              cookieStore.set(name, value, options);
            }
          } catch {
            // Called from a Server Component during render — safe to ignore since
            // middleware.ts refreshes the session on every request anyway.
          }
        },
      },
    }
  );
}
