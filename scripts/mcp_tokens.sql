-- 020-mcp-user-tokens: per-client MCP HTTP credentials
CREATE TABLE IF NOT EXISTS mcp_tokens (
    id bigserial PRIMARY KEY,
    label text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'reader')),
    token_hash text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz NULL,
    last_used_at timestamptz NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS mcp_tokens_active_label_uidx
    ON mcp_tokens (label)
    WHERE revoked_at IS NULL;
