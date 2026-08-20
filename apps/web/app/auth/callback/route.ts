import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

/**
 * OAuth (and email-link) callback for Supabase's PKCE flow — the provider redirects here with
 * a `code` query param after the user authenticates on Google's side; this exchanges it for a
 * session cookie via the server client, then sends the browser on to the dashboard. `next` lets
 * a caller round-trip back to wherever they started (defaults to the dashboard).
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(
    `${origin}/sign-in?error=${encodeURIComponent("Could not complete sign-in. Please try again.")}`
  );
}
