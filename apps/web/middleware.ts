import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

/**
 * Refreshes the Supabase session cookie on every request that isn't a static asset.
 * This only keeps the session alive; route-level access control still happens per-page
 * (e.g. redirecting unauthenticated users out of the authenticated app shell in Phase 3).
 *
 * Runs unconditionally on every request, so it must degrade gracefully rather than throw
 * when Supabase isn't configured yet (e.g. a fresh Phase 1 checkout before `.env` is filled
 * in) — auth-dependent features simply won't work until then, but the rest of the app
 * (including the public marketing pages) still has to render.
 */
export async function middleware(request: NextRequest) {
  let response = NextResponse.next({ request });

  if (!supabaseUrl || !supabasePublishableKey) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(
        "[middleware] NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY are not " +
          "set — skipping session refresh. See docs/CONTRIBUTING.md for Supabase setup."
      );
    }
    return response;
  }

  const supabase = createServerClient(supabaseUrl, supabasePublishableKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        for (const { name, value } of cookiesToSet) {
          request.cookies.set(name, value);
        }
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) {
          response.cookies.set(name, value, options);
        }
      },
    },
  });

  // Triggers a token refresh if the session is stale; required so Server Components
  // always see a valid session (they cannot refresh cookies themselves).
  await supabase.auth.getUser();

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
