# ai/

Standalone AI service layer, imported by `apps/api/app/ai`. Kept outside the API app so AI
logic is never scattered across route handlers and can be evaluated/tested independently.

```
pipelines/    multi-step AI pipelines (resume extraction, roadmap generation, interview eval)
prompts/      versioned prompt templates (never hardcoded inline in application code)
agents/       controlled agent workflows (Resume Analyst, Career Advisor, Interview Agent, ...)
embeddings/   embedding generation + caching utilities
evaluation/   LLM evaluation harness + test case fixtures
```

See [docs/AI_ARCHITECTURE.md](../docs/AI_ARCHITECTURE.md). Built starting Phase 5.
