# Product

## Register

product

## Users

Job seekers and career-changers using CareerAI to get an honest, data-backed read on where
they stand and what to do next — upload a resume, see an explainable score, compare their
skills against a real target role, and (as later phases ship) get matched to real jobs and
prep for interviews. They're actively working on their career, not casual browsers; often
checking this mid-search (time-pressured, a little anxious), sometimes exploring speculatively
(a curious professional planning ahead). Public content pages (landing, `/careers`,
`/skills/[slug]`) also serve a secondary, colder audience arriving from search — but the
product register still governs: these are real content pages in service of the tool, not a
separate marketing site.

## Product Purpose

Turn vague career anxiety into a concrete, explainable plan: what your resume actually says
about you, what a target role really requires, exactly which required skills you're missing,
and which real jobs fit once that phase ships. Every score, gap, and recommendation shows its
reasoning — never a bare number or a black-box verdict. Success looks like a user leaving with
one specific next action (a skill to learn, an application to send), not just a dashboard to
admire.

## Brand Personality

Confident, precise, quietly technical. A sharp technical mentor who shows their work, not
hype-y "AI will change your life" marketing. Calm competence over excitement — closer to a
well-built analytics/dev tool (Linear, a good internal dashboard) than a consumer growth app.

## Anti-references

Generic AI-SaaS visual language: cream/beige backgrounds, gradient text, hero-metric-card
templates, identical icon+heading+text card grids repeated section after section, a tiny
uppercase tracked eyebrow over every section, glassmorphism used decoratively. Also: over-
explaining/hand-holdy copy, fake urgency, and empty "coming soon" placeholders that read as
unfinished rather than intentional.

## Design Principles

- Show the work — every score, gap, or recommendation surfaces its reasoning (explanation +
  evidence), never a bare number.
- Confident, not guessing — the UI should read as deterministic and precise even where an LLM
  is involved under the hood; no hedging language, no wishy-washy states.
- One motion vocabulary, reused everywhere — a new feature's reveal/hover language should feel
  native on day one, not like a bolted-on animation invented just for it.
- Density with air, never dead air — dashboards can hold real information without feeling
  cramped, but no page should have unexplained empty space; every gap is intentional breathing
  room or it's a bug to fix.
- Public content pages are real content, not stripped-down utility views — they're also this
  product's SEO surface, so they earn genuine editorial layout quality, not a bare list.

## Accessibility & Inclusion

WCAG AA target. `prefers-reduced-motion` is already respected via a global `MotionConfig`
(motion collapses to instant rather than being removed for meaningful interactions like
drag-to-rotate). Dark/light theme parity is required for every new component.
