import { createClient } from "@/lib/supabase/client";

// A single shared browser client, not one per call. `createClient()` (lib/supabase/client.ts)
// is cheap to call but not free to call repeatedly in a burst: profile-page-client.tsx fires
// 6 `apiFetch` calls in one `Promise.all`, doubled to 12 by React Strict Mode in dev. Each
// fresh `createBrowserClient()` instance does its own storage read/init with no shared
// in-memory lock across instances, and under that burst some of those independently-
// initializing instances intermittently read an inconsistent session and sent no/stale
// Authorization header, surfacing as real 401s from the API — reproducible with real browser
// concurrency, not with curl or a plain `Promise.all` of `fetch` (neither spins up multiple
// client instances). One shared instance means one shared, consistent view of the session.
const supabase = createClient();

export class ApiError extends Error {
  status: number;
  code: string;
  /** Seconds to wait before retrying — read from the `Retry-After` response header (docs/API.md
   * §4's 429 contract). `null` for every other status; only rate-limited AI routes set it. */
  retryAfterSeconds: number | null;

  constructor(status: number, code: string, message: string, retryAfterSeconds: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

type Envelope<T> = { data: T; meta: { request_id: string | null; next_cursor: string | null } };
type ErrorEnvelope = {
  error: { code: string; message: string; details: unknown; request_id: string | null };
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

/**
 * Authenticated fetch wrapper for `/api/v1/*` — attaches the current Supabase session's
 * bearer token, unwraps the `{ data, meta }` envelope (docs/API.md §2), and throws `ApiError`
 * with the server's stable `code` on failure so callers can branch on it rather than parsing
 * prose. Browser-only (reads the session via the browser Supabase client) since every current
 * caller is a Client Component driving a form.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  // `FormData` bodies (file uploads) need the browser to set `Content-Type` itself — it
  // includes a multipart boundary that can't be hardcoded, so forcing `application/json`
  // here would silently break the request.
  const isFormData = init.body instanceof FormData;

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
      ...init.headers,
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.json();

  if (!response.ok) {
    const errorBody = body as ErrorEnvelope;
    const retryAfterHeader = response.headers.get("Retry-After");
    const retryAfterSeconds = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : null;
    throw new ApiError(
      response.status,
      errorBody.error?.code ?? "UNKNOWN_ERROR",
      errorBody.error?.message ?? "Something went wrong. Please try again.",
      Number.isFinite(retryAfterSeconds) ? retryAfterSeconds : null
    );
  }

  return (body as Envelope<T>).data;
}
