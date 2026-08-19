-- Runs once, on first container init (docker-entrypoint-initdb.d), against the database
-- created by POSTGRES_DB. See docs/DATABASE.md §1.
CREATE EXTENSION IF NOT EXISTS vector;
