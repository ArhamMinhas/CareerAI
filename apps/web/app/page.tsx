const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="rounded-full border border-border bg-surface px-4 py-1.5 text-sm text-muted-foreground">
        Phase 1 — Project Foundation
      </span>
      <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
        CareerAI
      </h1>
      <p className="max-w-md text-balance text-lg text-muted-foreground">
        The premium landing page ships in Phase 2. This confirms the app shell, design
        tokens, and dark/light theming are wired up correctly.
      </p>
      <a
        href={`${apiUrl}/api/v1/health`}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:opacity-90"
      >
        Check API health
      </a>
    </main>
  );
}
