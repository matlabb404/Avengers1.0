-- Customer contact (phone) + avatar columns.
--
-- Shown to vendors on received bookings and on the customer's own profile.
-- The `customer` table is lowercase, so no quoting is needed.
--
--   sudo -u postgres psql -d Avengers -f 002_customer_contact.sql
--
-- Idempotent: ADD COLUMN IF NOT EXISTS, so re-running is safe.

BEGIN;

ALTER TABLE customer
    ADD COLUMN IF NOT EXISTS phone           VARCHAR(50),
    ADD COLUMN IF NOT EXISTS avatar_asset_id UUID REFERENCES media_assets(id);

COMMIT;

-- Verify:
--   \d customer
-- expect the new phone + avatar_asset_id columns (avatar_asset_id FK -> media_assets).
