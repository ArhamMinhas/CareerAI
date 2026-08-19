import { createBrowserClient } from "@supabase/ssr";

/**
 * Browser-side Supabase client — only ever uses the public *publishable* key (safe to ship
 * to the client; RLS/JWT verification is what actually enforces access — see
 * docs/SECURITY.md §1). Never import the secret key here.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
  );
}
