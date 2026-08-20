# CareerAI — Database Design

Status: Phase 0 design. Implemented via SQLAlchemy/SQLModel models + Alembic migrations
starting Phase 1 (core identity tables) and extended per-phase (see [ROADMAP.md](./ROADMAP.md)).

## 1. Conventions

- **Engine:** PostgreSQL 15+ with the `pgvector` extension enabled (`CREATE EXTENSION vector`).
- **Primary keys:** `UUID` (`gen_random_uuid()`), never auto-increment integers — avoids
  enumeration attacks on public-ish IDs (jobs, resumes) and simplifies future multi-region setup.
- **Timestamps:** every table has `created_at timestamptz NOT NULL DEFAULT now()` and
  `updated_at timestamptz NOT NULL DEFAULT now()` (maintained by an `updated_at` trigger).
- **Soft deletion:** user-facing content tables (`resumes`, `projects`, `applications`, etc.)
  carry `deleted_at timestamptz NULL`; hard deletes are reserved for GDPR-style erasure requests
  and cascade explicitly. Reference/lookup tables (`skills`, `companies`, `jobs`) are hard-deleted
  by admins only.
- **Naming:** snake_case tables and columns, plural table names, `<entity>_id` FK columns.
- **Money:** `numeric(12,2)` with an explicit `currency` column — never `float`.
- **Enums:** implemented as Postgres `ENUM` types for fixed small sets (roles, statuses) so
  invalid values are rejected at the DB layer, not just in Pydantic.
- **Embeddings:** `vector(1536)` columns (OpenAI `text-embedding-3-small` dimension; configurable
  per [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md)), indexed with `ivfflat` (cosine ops) once a
  table has enough rows to benefit (roughly >10k).

## 2. Entity groups (ERDs)

The full schema is 32 tables; splitting into logical groups keeps each diagram readable. Every
table is defined in detail in §3.

### 2.1 Identity & Profile

```mermaid
erDiagram
    USERS ||--o| PROFILES : has
    USERS ||--o{ RESUMES : owns
    USERS ||--o{ CAREER_GOALS : sets
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_LOGS : generates
    PROFILES ||--o{ EDUCATION : lists
    PROFILES ||--o{ EXPERIENCE : lists
    PROFILES ||--o{ PROJECTS : lists
    PROFILES ||--o{ USER_SKILLS : lists

    USERS {
        uuid id PK
        text email UK
        text hashed_password
        enum role "USER | ADMIN | RECRUITER"
        boolean email_verified
        timestamptz created_at
    }
    PROFILES {
        uuid id PK
        uuid user_id FK
        text full_name
        text headline
        text location
        text avatar_url
        text bio
    }
    CAREER_GOALS {
        uuid id PK
        uuid user_id FK
        text target_role
        text target_industry
        int target_years_experience
        boolean is_active
    }
    EDUCATION {
        uuid id PK
        uuid profile_id FK
        text institution
        text degree
        text field_of_study
        date start_date
        date end_date "null = currently enrolled"
        text description
        timestamptz deleted_at "soft delete, §1"
    }
    EXPERIENCE {
        uuid id PK
        uuid profile_id FK
        text company
        text title
        text location
        text employment_type
        date start_date
        date end_date "null = current role"
        text description
        timestamptz deleted_at "soft delete, §1"
    }
    PROJECTS {
        uuid id PK
        uuid profile_id FK
        text title
        text description
        text url
        text repo_url
        date start_date
        date end_date
        timestamptz deleted_at "soft delete, §1"
    }
```

**Revised in Phase 4:** the full resume-extraction result (education/experience/projects, not
just skills) lives in `resumes.structured_data` (jsonb) instead of being merged into these
tables directly — merging would need real dedup/conflict-resolution UX (what happens when a
resume's "MIT 2018-2022" collides with a manually-entered "MIT 2018-2021"?) that hasn't been
designed. Only `SKILLS`/`USER_SKILLS` get auto-synced from a resume (additive, never
overwrites — see §2.2), since that's a simple "does this skill exist yet" check, not a
structural merge. Revisit if/when profile auto-fill from a parsed resume is actually wanted.

### 2.2 Resume & Skills

```mermaid
erDiagram
    RESUMES ||--o{ RESUME_VERSIONS : has
    RESUMES ||--o{ USER_SKILLS : "syncs skills into (additive, source=resume)"
    RESUMES ||--o| EMBEDDINGS : "has (Phase 5+)"
    SKILLS ||--o{ USER_SKILLS : referenced_by
    SKILLS ||--o{ JOB_SKILLS : referenced_by
    SKILLS ||--o{ SKILL_GAPS : referenced_by
    SKILLS ||--o{ SKILL_DEMAND : tracked_by

    RESUMES {
        uuid id PK
        uuid user_id FK
        text file_url "storage path, not a public URL — see §1 storage note below"
        text file_name "original upload filename"
        text file_type "PDF|DOCX"
        enum status "uploaded|processing|completed|failed"
        text failure_reason "set only when status=failed"
        jsonb structured_data "full extraction: contact, summary, skills, experience, education, projects"
        numeric overall_score
        jsonb score_breakdown "per-sub-score {score, explanation, evidence} map"
        timestamptz deleted_at "soft delete, §1"
    }
    RESUME_VERSIONS {
        uuid id PK
        uuid resume_id FK
        int version_number
        jsonb structured_data
        numeric overall_score
        jsonb score_breakdown
    }
    SKILLS {
        uuid id PK
        text name UK
        text slug UK
        text category
        text[] synonyms "Phase 6"
        text seo_summary "Phase 6"
        vector embedding "Phase 6"
    }
    USER_SKILLS {
        uuid id PK
        uuid profile_id FK
        uuid skill_id FK
        uuid resume_id FK "null until Phase 4 wires resume-parsed skills in"
        enum proficiency "beginner|intermediate|advanced|expert"
        enum source "resume|manual|interview — Phase 3 only ever writes manual"
    }
```

Phase 3 ships `SKILLS.name`/`slug`/`category` only — `synonyms`/`seo_summary`/`embedding`
are added by a later migration once Phase 6 (skill-gap engine, public `/skills/[slug]` pages)
actually needs them, rather than reserving unused columns now.

### 2.3 Jobs & Matching

```mermaid
erDiagram
    COMPANIES ||--o{ JOBS : posts
    JOBS ||--o{ JOB_SKILLS : requires
    JOBS ||--o{ JOB_MATCHES : matched_in
    JOBS ||--o{ APPLICATIONS : receives
    JOBS ||--o| EMBEDDINGS : has
    USERS ||--o{ JOB_MATCHES : receives
    USERS ||--o{ APPLICATIONS : submits
    USERS ||--o{ SKILL_GAPS : has

    COMPANIES {
        uuid id PK
        text name
        text slug UK
        text industry
        text logo_url
        text description
    }
    JOBS {
        uuid id PK
        uuid company_id FK
        text title
        text description
        text seniority_level
        text employment_type
        text location
        boolean remote
        numeric salary_min
        numeric salary_max
        text currency
        vector embedding
        timestamptz posted_at
    }
    JOB_SKILLS {
        uuid id PK
        uuid job_id FK
        uuid skill_id FK
        boolean is_required
        int weight
    }
    JOB_MATCHES {
        uuid id PK
        uuid user_id FK
        uuid job_id FK
        numeric match_score
        jsonb score_breakdown
        text explanation
    }
    APPLICATIONS {
        uuid id PK
        uuid user_id FK
        uuid job_id FK
        enum status "saved|applied|interviewing|offer|rejected"
        timestamptz applied_at
    }
    SKILL_GAPS {
        uuid id PK
        uuid user_id FK
        uuid skill_id FK
        text target_role
        enum gap_level "missing|weak|adequate|strong"
        int priority
    }
```

### 2.4 Learning, Interviews & AI

```mermaid
erDiagram
    LEARNING_PATHS ||--o{ LEARNING_RESOURCES : contains
    USERS ||--o{ LEARNING_PATHS : follows
    USERS ||--o{ INTERVIEWS : takes
    INTERVIEWS ||--o{ INTERVIEW_QUESTIONS : contains
    INTERVIEW_QUESTIONS ||--o| INTERVIEW_ANSWERS : answered_by
    INTERVIEW_ANSWERS ||--o| INTERVIEW_EVALUATIONS : scored_by
    USERS ||--o{ AI_CONVERSATIONS : has

    LEARNING_PATHS {
        uuid id PK
        uuid user_id FK
        text target_role
        jsonb phases
        enum status "active|completed|abandoned"
    }
    LEARNING_RESOURCES {
        uuid id PK
        uuid learning_path_id FK
        uuid skill_id FK
        text title
        text url
        text resource_type "course|article|project|docs"
        int estimated_hours
        boolean completed
    }
    INTERVIEWS {
        uuid id PK
        uuid user_id FK
        text mode "technical|behavioral|hr|system_design|ml|data_science"
        text target_role
        enum status "in_progress|completed|abandoned"
        numeric overall_score
    }
    INTERVIEW_QUESTIONS {
        uuid id PK
        uuid interview_id FK
        text question_text
        text category
        int order_index
        vector embedding
    }
    INTERVIEW_ANSWERS {
        uuid id PK
        uuid question_id FK
        text answer_text
        int response_time_seconds
    }
    INTERVIEW_EVALUATIONS {
        uuid id PK
        uuid answer_id FK
        numeric correctness_score
        numeric depth_score
        numeric communication_score
        text feedback
    }
    AI_CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        text feature "resume_analysis|career_advisor|interview|rag_chat"
        text model
        int prompt_tokens
        int completion_tokens
        int latency_ms
        jsonb request_meta
    }
```

### 2.5 Market Intelligence & System

```mermaid
erDiagram
    SKILLS ||--o{ SKILL_DEMAND : measured
    MARKET_TRENDS ||--o{ SALARY_DATA : includes

    MARKET_TRENDS {
        uuid id PK
        text category
        text region
        jsonb metrics
        date period_start
        date period_end
    }
    SKILL_DEMAND {
        uuid id PK
        uuid skill_id FK
        text region
        int demand_count
        numeric growth_rate
        date period
    }
    SALARY_DATA {
        uuid id PK
        text job_title
        text region
        text seniority_level
        numeric p25
        numeric p50
        numeric p75
        text currency
        date period
    }
    NOTIFICATIONS {
        uuid id PK
        uuid user_id FK
        text type
        text title
        text body
        boolean read
        timestamptz created_at
    }
    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        text action
        text resource_type
        uuid resource_id
        jsonb metadata
        text ip_address
        timestamptz created_at
    }
    EMBEDDINGS {
        uuid id PK
        text owner_type "resume|job|skill|learning_resource|interview_question|career_path|resource|kb_chunk"
        uuid owner_id
        vector embedding
        text model
        timestamptz created_at
    }
```

`EMBEDDINGS` is a polymorphic table used for RAG knowledge-base chunks and any owner type that
doesn't warrant its own dedicated `vector` column; high-traffic lookups (skills, jobs) keep a
denormalized `vector` column directly on the entity table for join-free similarity search.

### 2.6 Public Content & SEO

Two tables back the SEO-indexable, publicly-crawlable content routes in
[SEO.md §1](./SEO.md#1-what-gets-indexed-vs-what-doesnt) (`/careers/[slug]`, `/skills/[slug]`,
`/companies/[id]`, `/resources/[slug]`). Both are deliberately **dual-purpose**: the same row
that renders a public SEO page also feeds the product's own AI features, so content is authored
once, not duplicated between "marketing content" and "app data."

```mermaid
erDiagram
    CAREER_PATHS ||--o{ CAREER_PATH_SKILLS : requires
    SKILLS ||--o{ CAREER_PATH_SKILLS : referenced_by
    RESOURCES ||--o{ LEARNING_RESOURCES : linked_from

    CAREER_PATHS {
        uuid id PK
        text slug UK
        text title
        text summary
        text description_md
        text[] related_job_titles
        vector embedding
        boolean published
        timestamptz created_at
    }
    CAREER_PATH_SKILLS {
        uuid id PK
        uuid career_path_id FK
        uuid skill_id FK
        int weight
        boolean is_core
    }
    RESOURCES {
        uuid id PK
        text slug UK
        text title
        text summary
        text body_md
        text category
        text[] tags
        vector embedding
        boolean published
        timestamptz published_at
        timestamptz updated_at
    }
```

- `CAREER_PATHS` is what `/careers/[slug]` (e.g. `/careers/ai-engineer`) renders, and is the
  same curated role/skill profile the Skill Gap Engine diffs a user's skills against
  ([ML_PIPELINE.md §2.3](./ML_PIPELINE.md#23-skill-gap-classification)) — `CAREER_PATH_SKILLS`
  is the structured join the gap engine reads; `description_md`/`summary` is what the public page
  renders.
- `RESOURCES` is what `/resources/[slug]` renders **and** the source content the RAG knowledge
  base ingests ([AI_ARCHITECTURE.md §6](./AI_ARCHITECTURE.md#6-rag-pipeline)) — `kb_ingest.py`
  chunks `body_md` into `EMBEDDINGS` rows for retrieval, while the same row is served directly
  (rendered from `body_md`) as a public article page. `resources.embedding` is a whole-document
  embedding used for "related articles" internal linking; per-chunk embeddings for RAG retrieval
  live in `EMBEDDINGS` (`owner_type = 'resource'`).
- `published`/`published_at` gates what's in the sitemap and public API responses — draft rows
  are queryable internally (e.g. by an admin editor, Phase 13) but never served publicly or
  indexed.
- `COMPANIES` (§2.3) already backs `/companies/[id]`; no new table needed there beyond the
  `slug`/`description` columns added above.

## 3. Indexing strategy

| Table | Index | Purpose |
|---|---|---|
| `users` | unique btree on `email` | login lookup |
| `resumes` | btree on `(user_id, created_at desc)` | "my resumes" list |
| `jobs` | ivfflat on `embedding` (cosine) | semantic job search |
| `jobs` | btree on `(remote, location)`, gin on `to_tsvector(title, description)` | filter + keyword fallback search |
| `job_matches` | unique btree on `(user_id, job_id)`, btree on `(user_id, match_score desc)` | dedupe + ranked match list |
| `user_skills` | unique btree on `(profile_id, skill_id)` | dedupe |
| `job_skills` | unique btree on `(job_id, skill_id)` | dedupe |
| `skills` | ivfflat on `embedding`, unique btree on `name`, unique btree on `slug` | synonym-robust skill resolution + `/skills/[slug]` lookup |
| `companies` | unique btree on `slug` | `/companies/[id]` (slug-in-URL) lookup |
| `career_paths` | unique btree on `slug`, partial btree on `slug WHERE published` | `/careers/[slug]` lookup + sitemap generation |
| `resources` | unique btree on `slug`, btree on `(published, published_at desc)` | `/resources/[slug]` lookup + sitemap/listing ordering |
| `ai_conversations` | btree on `(user_id, created_at desc)`, btree on `(feature, created_at)` | cost/usage dashboards |
| `audit_logs` | btree on `(user_id, created_at desc)` | admin audit trail |
| `embeddings` | ivfflat on `embedding`, btree on `(owner_type, owner_id)` | RAG retrieval |

## 4. Data integrity rules

- `resumes.status` transitions are enforced in the service layer as a state machine
  (`uploaded → processing → completed|failed`); the DB constrains the enum values only.
- `job_matches.match_score` and `skill_gaps.priority` are **written by the recommendation
  service**, never computed in SQL or by the LLM directly — see [ML_PIPELINE.md](./ML_PIPELINE.md)
  and [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md).
- Foreign keys from content tables to `users`/`profiles` use `ON DELETE CASCADE` for owned data
  (education, experience, projects) and `ON DELETE SET NULL` for cross-references that should
  survive (e.g. `audit_logs.user_id` after account deletion, for compliance retention).
- `career_goals` allows multiple rows per user but only one `is_active = true` at a time
  (partial unique index `WHERE is_active`).

## 5. Migrations

Alembic manages schema changes from Phase 1 onward. One migration per logical change (not one
giant "initial schema" migration per phase) so history stays reviewable. Migration naming:
`YYYYMMDDHHMM_<verb>_<subject>.py` (e.g. `202601151030_add_job_matches_table.py`).
