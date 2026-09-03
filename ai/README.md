# ai/

Still just this README as of Phase 5 — a deliberate deviation from the original plan, not an
oversight. The provider abstraction, prompt registry, embeddings, and conversation logging all
live in `apps/api/app/ai/` and `apps/api/app/services/` instead: no notebook or standalone `ml/`
consumer exists yet to need a framework-agnostic top-level package, the API and worker already
share that codebase/Docker image, and a real top-level package would need Docker
`COPY`/`PYTHONPATH` changes for no current benefit. Same reasoning as `packages/ui` staying a
stub since Phase 2.

See [docs/AI_ARCHITECTURE.md](../docs/AI_ARCHITECTURE.md) and
[docs/ROADMAP.md](../docs/ROADMAP.md)'s Phase 5 entry. Revisit if a genuinely separate consumer
(e.g. a notebook or standalone ML job under `ml/`) shows up.

Still true as of Phase 9: the RAG pipeline (ingestion, retrieval, generation) and its evaluation
harness live in `apps/api/app/ai/` too, not here — same reasoning, no new consumer appeared.
