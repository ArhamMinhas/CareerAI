import { createBrowserClient } from "@supabase/ssr";

/**
 * Browser-side Supabase client — only ever uses the public anon key (safe to ship to the
 * client; RLS/JWT verification is what actually enforces access). Never import the service
 * role key here. See docs/SECURITY.md §1.
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
