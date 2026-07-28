-- Complete text_ok papers -> indexed
UPDATE papers p
SET ingest_status = 'indexed',
    ingest_error = NULL,
    updated_at = NOW()
WHERE p.ingest_status = 'text_ok'
  AND EXISTS (SELECT 1 FROM chunks c WHERE c.paper_id = p.id)
  AND NOT EXISTS (
      SELECT 1 FROM chunks c
      WHERE c.paper_id = p.id AND c.embedding IS NULL
  );

-- Incomplete text_ok papers -> failed
UPDATE papers p
SET ingest_status = 'failed',
    ingest_error = 'legacy incomplete ingest; run Add again',
    updated_at = NOW()
WHERE p.ingest_status = 'text_ok'
  AND (
      NOT EXISTS (SELECT 1 FROM chunks c WHERE c.paper_id = p.id)
      OR EXISTS (
          SELECT 1 FROM chunks c
          WHERE c.paper_id = p.id AND c.embedding IS NULL
      )
  );