type Envelope<T> = { data: T; meta: { request_id: string | null; next_cursor: string | null } };

// `API_INTERNAL_URL` (server-only, no `NEXT_PUBLIC_` prefix — never bundled into client JS)
// takes priority over `NEXT_PUBLIC_API_URL` here because this module only ever runs
// server-side (SSR/SSG for the public content pages), and inside Docker those two URLs are
// genuinely different: `NEXT_PUBLIC_API_URL` is `http://localhost:8000` for the *browser* to
// reach the api container through its published port, but a fetch from *inside* the web
// container to that same address hits the web container's own loopback, not the api
// container — it needs the Docker-network service name instead (`http://api:8000`, set via
// docker-compose.yml). Outside Docker (plain `npm run build`/`next dev` on a host machine)
// there's no `API_INTERNAL_URL`, so this falls through to `NEXT_PUBLIC_API_URL`, then to a
// bare localhost default so an environment missing both still gets a working URL instead of
// "Failed to parse URL from undefined/...".
const API_BASE =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class PublicApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "PublicApiError";
    this.status = status;
  }
}

/**
 * Server-side fetch for public, unauthenticated `/api/v1/*` endpoints — used by the SSG/ISR
 * public content pages (`/careers`, `/careers/[slug]`, `/skills/[slug]`), never by Client
 * Components (those use `apiFetch` in lib/api.ts, which attaches the browser session).
 * `revalidateSeconds` maps directly onto Next's fetch cache (`next: { revalidate }`), per
 * docs/SEO.md §2.3/§5's ISR strategy for curated content — hours, not minutes, since this
 * content changes far less often than jobs.
 */
export async function fetchPublic<T>(path: string, revalidateSeconds: number): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: revalidateSeconds },
  });

  if (!response.ok) {
    throw new PublicApiError(
      response.status,
      response.status === 404 ? "Not found" : `Request to ${path} failed`
    );
  }

  const envelope = (await response.json()) as Envelope<T>;
  return envelope.data;
}
