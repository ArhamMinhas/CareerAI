# CareerAI — Frontend / UI Architecture

Status: Phase 0 design. Shell, design tokens, and navigation built in Phase 1–2; feature
routes added per phase. See [ROADMAP.md](./ROADMAP.md). For discoverability after deployment
(metadata, sitemaps, structured data), see [SEO.md](./SEO.md) — this document covers the
component/rendering architecture that SEO strategy depends on.

## 1. Route map (`apps/web/app`)

```
/                          marketing landing page (public)
/dashboard                 executive overview
/profile                   profile, education, experience, projects, skills, goals
/resume                    resume list
/resume/analyze            upload + processing + analysis view
/skills                    skill inventory + gap visualization
/career                    recommendations + explanations
/jobs                      browse/search
/jobs/[id]                 job detail
/matches                   personalized ranked matches
/roadmap                   learning roadmap
/interviews                history
/interviews/[id]           session (question/answer/evaluation)
/analytics                 market + personal analytics
/settings                  account, notifications, theme

/admin                     (role=ADMIN)
/admin/users
/admin/jobs
/admin/analytics
/admin/datasets
/admin/models
/admin/system
```

Public routes (`/`, marketing pages) are the SEO surface — see [SEO.md](./SEO.md). Everything
under an authenticated layout (`/dashboard` and below) is intentionally **not** indexed
(`noindex`, excluded from the sitemap) since it's private, personalized data.

## 2. Rendering strategy

- **Server Components by default.** Data-fetching pages (landing sections, job listing SSR for
  first paint + SEO, dashboard shell) render on the server.
- **Client Components only where interactivity requires it:** forms (React Hook Form + Zod),
  charts, the 3D canvas, animated sequences, anything using browser-only APIs or local state.
  A Client Component is a leaf, not a whole page — server components pass data down to small
  client islands rather than the reverse (spec §3).
- **Server Actions** for simple mutations that don't need the full REST contract (e.g. marking
  a notification read) where it reduces client-side boilerplate; anything AI-triggering or
  business-critical goes through the versioned REST API in [API.md](./API.md) so the backend
  remains the single source of truth and validation layer.
- **Streaming UI** (`loading.tsx`, React `Suspense`) for slower data (AI-heavy dashboard cards)
  so the shell paints immediately and cards populate progressively.

## 3. State management

| State category | Tool | Why |
|---|---|---|
| Server/remote data (resumes, jobs, matches, analytics) | TanStack Query | Caching, background refetch, request dedup, works naturally with polling (resume processing status) and SSE (interview/chat streaming) |
| Form state | React Hook Form + Zod | Schema-shared validation mirroring backend Pydantic schemas (`packages/types`) |
| Ephemeral UI state (modals, tabs, theme) | Local component state / lightweight Zustand store where state is cross-component | Avoid a heavyweight global store for what's fundamentally local UI state |
| Auth/session | Supabase client SDK + server-side session helpers | Session lives in httpOnly cookies where possible; never store the JWT in `localStorage` |

## 4. Design system (`packages/ui` + design tokens)

- **Tokens first:** color, spacing, radius, shadow, and type-scale tokens defined once
  (Tailwind config in `packages/config`) and consumed by both `packages/ui` and `apps/web` —
  no ad hoc hex codes or magic spacing values in component code (spec §41).
- **Component inventory:** Button, Input, Select, Modal, Drawer, Toast, Card, Badge, Tabs,
  Dropdown, Tooltip, Skeleton, Progress, Chart (Recharts wrapper), DataTable, CommandPalette,
  Navbar, Sidebar, Breadcrumb, EmptyState, ErrorState, LoadingState — each with documented
  props, states (default/hover/focus/disabled/loading), and a light+dark rendering.
- **Dark/light mode:** CSS variables switched via a `data-theme` attribute (matches system
  preference by default, user-overridable, persisted).
- **Visual language:** glassmorphism used sparingly (cards on the landing page/dashboard hero
  areas), subtle gradients, soft shadows, thin borders, generous whitespace — restrained rather
  than maximal, per spec §8 ("avoid excessive visual effects").

## 5. Animation system

| Layer | Tool | Used for |
|---|---|---|
| Component-level | Framer Motion | Page transitions, card entrances, hover states, modal/drawer open-close, layout animations |
| Scroll-driven sequences | GSAP (+ ScrollTrigger) | Landing page hero timeline, scroll-triggered section reveals |
| Smooth scroll | Lenis | Landing page and long content pages |
| 3D | React Three Fiber / drei | See §6 |

Rules: every animation respects `prefers-reduced-motion` (swap to instant/opacity-only
transitions); animations never gate interactivity (a card is clickable before its entrance
animation finishes); no animation is added purely decoratively without a UX purpose
(orientation, feedback, continuity) — spec §42/§43.

## 6. 3D strategy

3D is scoped to three specific surfaces, each with a defined non-3D fallback:

| Surface | 3D treatment | Fallback |
|---|---|---|
| Landing hero | Interactive skill/career network — floating nodes, connecting lines, particles, subtle parallax on mouse move | Static/CSS gradient + 2D SVG node graph on low-end devices or `prefers-reduced-motion` |
| Dashboard (optional) | Skill constellation / career progression graph | 2D force-directed graph (e.g. via a lightweight canvas/D3 layout) |
| Resume/AI analysis | Animated "processing" visualization | CSS-based skeleton/progress animation |

Implementation discipline (spec §9):
- Lazy-loaded (`next/dynamic`, `ssr: false`) so the Three.js bundle never blocks first paint or
  non-3D routes.
- Device capability check (rough heuristic: `navigator.hardwareConcurrency`, connection type,
  a WebGL support check) gates whether the 3D canvas mounts at all; mobile and low-end desktop
  get the CSS/2D fallback by default.
- Low-poly geometry, instanced meshes for repeated nodes, capped particle counts, and a frame
  budget — the 3D scene is profiled against a target frame time, not built and left unmeasured.
- `prefers-reduced-motion` disables camera drift/auto-rotation even when the 3D canvas is shown.

## 7. Responsive design

Mobile is a distinct layout, not a shrunk desktop layout (spec §35): bottom navigation on
mobile for the authenticated app shell (vs. a sidebar on desktop), collapsible sidebar on
tablet, touch-target sizing (min 44×44px), charts that reflow to stacked/simplified views
below a breakpoint rather than shrinking illegibly, and the 3D hero degrading per §6.

## 8. Accessibility

Semantic HTML first; ARIA only to fill genuine gaps (custom Select/Combobox, CommandPalette).
Full keyboard navigation including the command palette and modal focus trapping. Color tokens
are chosen to meet WCAG AA contrast in both themes (validated, not assumed). Focus states are
visible and match the design language (not just the browser default outline removed with
nothing replacing it). Charts include a text/table alternative for screen readers.

## 9. Error/loading/empty states

Every data-bearing view implements five states explicitly (spec §44): loading (skeleton, not a
spinner-only blank screen), success, empty (with a clear next action — e.g. "Upload your first
resume"), error (human-readable, with retry), and retry-in-progress. These are `packages/ui`
components (`EmptyState`, `ErrorState`, `Skeleton`) reused across features rather than
re-implemented per page.

## 10. Performance budget

Code-split by route; heavy libraries (Three.js, chart library) loaded only on routes that use
them; images served via `next/image` with responsive sizes; fonts subset and self-hosted with
`font-display: swap`. Bundle size and Core Web Vitals (LCP/INP/CLS) are tracked as CI checks
starting Phase 15, and matter directly for SEO ranking — see [SEO.md §4](./SEO.md#4-core-web-vitals--performance-as-a-ranking-factor).
