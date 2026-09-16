CREATE TABLE IF NOT EXISTS communities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_en  TEXT NOT NULL
);

ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS community_id UUID REFERENCES communities(id);

CREATE INDEX IF NOT EXISTS idx_papers_community_id ON papers (community_id);
