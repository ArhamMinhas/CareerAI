export type Resource = {
  id: string;
  slug: string;
  title: string;
  summary: string;
  category: string | null;
  tags: string[] | null;
  updated_at: string;
};

export type ResourceDetail = Resource & {
  body_md: string;
  related_resources: Resource[];
};

/** `POST /api/v1/rag/query` (docs/AI_ARCHITECTURE.md §6, Phase 9) — backs `/dashboard/ask`. */
export type RagCitation = {
  resource_slug: string;
  resource_title: string;
};

export type RagQueryResponse = {
  answer: string;
  citations: RagCitation[];
};
