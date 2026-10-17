-- ============================================================================
-- Chat: multi-attachments (photos + files), shared-post payload, reply threading
-- ============================================================================
-- Base.metadata.create_all() creates NEW tables but does NOT add columns to
-- existing ones. Run this once against any already-provisioned database. It's
-- idempotent — safe to re-run. On a fresh DB you can skip it; create_all builds
-- everything from the models.

BEGIN;

-- 1) Persist the original filename so FILE chat attachments have a display name.
ALTER TABLE media_assets
    ADD COLUMN IF NOT EXISTS filename VARCHAR;

-- 2) Message-to-message reply threading (self-referential, same conversation).
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS reply_to_message_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'messages_reply_to_message_id_fkey'
    ) THEN
        ALTER TABLE messages
            ADD CONSTRAINT messages_reply_to_message_id_fkey
            FOREIGN KEY (reply_to_message_id) REFERENCES messages(id);
    END IF;
END $$;

-- 3) Ordered attachments: 0..N media assets (image/video/file) per message.
CREATE TABLE IF NOT EXISTS message_attachments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id  UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    asset_id    UUID NOT NULL REFERENCES media_assets(id),
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_message_attachment_message
    ON message_attachments (message_id, position);

-- 4) Backfill: surface pre-existing single-image messages as one attachment row
--    so they render through the new `attachments` path too. (Harmless if none.)
INSERT INTO message_attachments (message_id, asset_id, position)
SELECT m.id, m.asset_id, 0
FROM messages m
WHERE m.asset_id IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM message_attachments a WHERE a.message_id = m.id
  );

COMMIT;
