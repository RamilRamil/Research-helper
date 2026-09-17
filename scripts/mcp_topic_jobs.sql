-- 025-mcp-topic-ingest: durable topic ingest jobs for MCP admin agents
CREATE TABLE IF NOT EXISTS mcp_topic_jobs (
    id bigserial PRIMARY KEY,
    topic text NOT NULL,
    status text NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    creator_credential_id bigint REFERENCES mcp_tokens(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz NULL,
    error text NULL,
    found_count integer NOT NULL DEFAULT 0,
    indexed_count integer NOT NULL DEFAULT 0,
    failed_count integer NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS mcp_topic_jobs_status_id_idx
    ON mcp_topic_jobs (status, id);
