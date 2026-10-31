-- Vendor settlement / Paystack split-payout columns.
--
-- Run manually on the VPS (create_all only creates new tables, it never ALTERs
-- an existing one). The table is PascalCase, so it MUST be quoted as "Vendor".
--
--   sudo -u postgres psql -d Avengers -f 001_vendor_settlement.sql
--
-- Idempotent: ADD COLUMN IF NOT EXISTS, so re-running is safe.

BEGIN;

ALTER TABLE "Vendor"
    ADD COLUMN IF NOT EXISTS paystack_subaccount_code  VARCHAR,
    ADD COLUMN IF NOT EXISTS payout_channel            VARCHAR,   -- 'BANK' | 'MOMO'
    ADD COLUMN IF NOT EXISTS settlement_bank           VARCHAR,   -- Paystack bank/MoMo code
    ADD COLUMN IF NOT EXISTS settlement_account_number VARCHAR,
    ADD COLUMN IF NOT EXISTS settlement_account_name   VARCHAR;

-- Matches Column(..., index=True) on paystack_subaccount_code.
CREATE INDEX IF NOT EXISTS ix_vendor_paystack_subaccount_code
    ON "Vendor" (paystack_subaccount_code);

COMMIT;

-- Verify:
--   \d "Vendor"
-- expect the five new columns + the ix_vendor_paystack_subaccount_code index.
