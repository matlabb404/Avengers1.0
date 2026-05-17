-- ═══════════════════════════════════════════════════════════════
-- Migration: Payment System + Booking Updates + Price History
-- Date: 2026-05-17 (v2 — fixed table casing for actual schema)
-- Idempotent: safe to run multiple times
-- ═══════════════════════════════════════════════════════════════

BEGIN;

-- Required for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─────────────────────────────────────────────────────────────
-- 1. CREATE ENUMS
-- ─────────────────────────────────────────────────────────────

DO $$ BEGIN
    CREATE TYPE bookingstatus AS ENUM (
        'INIT', 'PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE currency AS ENUM (
        'GHS', 'NGN', 'KES', 'USD', 'EUR'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE paymentstatus AS ENUM (
        'PENDING', 'PROCESSING', 'SUCCEEDED', 'FAILED',
        'CANCELLED', 'REFUNDED', 'PARTIALLY_REFUNDED'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE paymentprovider AS ENUM (
        'PAYSTACK', 'HUBTEL', 'FLUTTERWAVE', 'STRIPE', 'MANUAL'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;


-- ─────────────────────────────────────────────────────────────
-- 2. UPDATE add_service TABLE (no-op since columns don't exist)
-- ─────────────────────────────────────────────────────────────

ALTER TABLE add_service DROP COLUMN IF EXISTS price_minor;
ALTER TABLE add_service DROP COLUMN IF EXISTS currency;


-- ─────────────────────────────────────────────────────────────
-- 3. UPDATE price_history TABLE
-- ─────────────────────────────────────────────────────────────

ALTER TABLE price_history
    ADD COLUMN IF NOT EXISTS price_minor INTEGER NOT NULL DEFAULT 0;

ALTER TABLE price_history
    ADD COLUMN IF NOT EXISTS currency currency NOT NULL DEFAULT 'GHS';

ALTER TABLE price_history
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE
    NOT NULL DEFAULT (now() AT TIME ZONE 'UTC');

ALTER TABLE price_history
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE
    NOT NULL DEFAULT (now() AT TIME ZONE 'UTC');

CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'UTC');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_price_history_updated_at ON price_history;
CREATE TRIGGER trg_price_history_updated_at
    BEFORE UPDATE ON price_history
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_timestamp();


-- ─────────────────────────────────────────────────────────────
-- 4. UPDATE booking TABLE
-- ─────────────────────────────────────────────────────────────

ALTER TABLE booking
    ADD COLUMN IF NOT EXISTS price_minor_at_booking INTEGER NOT NULL DEFAULT 0;

ALTER TABLE booking
    ADD COLUMN IF NOT EXISTS currency_at_booking currency NOT NULL DEFAULT 'GHS';

ALTER TABLE booking
    ADD COLUMN IF NOT EXISTS payment_status paymentstatus NOT NULL DEFAULT 'PENDING';

-- Convert booking.status from TEXT to bookingstatus enum
DO $$
DECLARE
    col_type TEXT;
BEGIN
    SELECT data_type INTO col_type
    FROM information_schema.columns
    WHERE table_name = 'booking' AND column_name = 'status';
    
    IF col_type IN ('text', 'character varying') THEN
        -- Normalize existing string values
        UPDATE booking SET status = UPPER(status)
        WHERE status IN ('init', 'pending', 'confirmed', 'cancelled', 'completed');
        
        -- Map unexpected values to INIT
        UPDATE booking SET status = 'INIT'
        WHERE status NOT IN ('INIT', 'PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED');
        
        ALTER TABLE booking ALTER COLUMN status DROP DEFAULT;
        
        ALTER TABLE booking
            ALTER COLUMN status TYPE bookingstatus
            USING status::bookingstatus;
        
        ALTER TABLE booking
            ALTER COLUMN status SET DEFAULT 'INIT'::bookingstatus;
    END IF;
END $$;


-- ─────────────────────────────────────────────────────────────
-- 5. CREATE payment TABLE
--    NOTE: References users (lowercase) and "Vendor" (PascalCase)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS payment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    booking_id UUID NOT NULL REFERENCES booking(booking_id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    vendor_id UUID NOT NULL REFERENCES "Vendor"(vendor_id) ON DELETE RESTRICT,
    
    amount_minor INTEGER NOT NULL,
    currency currency NOT NULL,
    
    provider paymentprovider NOT NULL,
    provider_reference VARCHAR(100) NOT NULL UNIQUE,
    provider_transaction_id VARCHAR(100),
    
    status paymentstatus NOT NULL DEFAULT 'PENDING',
    
    provider_metadata JSONB,
    failure_reason TEXT,
    
    platform_fee_minor INTEGER NOT NULL DEFAULT 0,
    vendor_payout_minor INTEGER NOT NULL DEFAULT 0,
    
    idempotency_key VARCHAR(100) UNIQUE,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    paid_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_payment_booking_id ON payment(booking_id);
CREATE INDEX IF NOT EXISTS idx_payment_user_id ON payment(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_vendor_id ON payment(vendor_id);
CREATE INDEX IF NOT EXISTS idx_payment_status ON payment(status);
CREATE INDEX IF NOT EXISTS idx_payment_provider_reference ON payment(provider_reference);

DROP TRIGGER IF EXISTS trg_payment_updated_at ON payment;
CREATE TRIGGER trg_payment_updated_at
    BEFORE UPDATE ON payment
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_timestamp();


-- ─────────────────────────────────────────────────────────────
-- 6. CREATE refund TABLE
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS refund (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    payment_id UUID NOT NULL REFERENCES payment(id) ON DELETE RESTRICT,
    
    amount_minor INTEGER NOT NULL,
    currency currency NOT NULL,
    
    status paymentstatus NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    
    provider_refund_id VARCHAR(100),
    provider_metadata JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_refund_payment_id ON refund(payment_id);


-- ─────────────────────────────────────────────────────────────
-- 7. CREATE webhook_event TABLE
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS webhook_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    provider paymentprovider NOT NULL,
    event_id VARCHAR(200) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    
    payload JSONB NOT NULL,
    
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'UTC'),
    processed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT uq_webhook_event_provider_event_id UNIQUE (provider, event_id)
);

CREATE INDEX IF NOT EXISTS idx_webhook_event_provider ON webhook_event(provider);
CREATE INDEX IF NOT EXISTS idx_webhook_event_processed ON webhook_event(processed);


-- ─────────────────────────────────────────────────────────────
-- 8. BACKFILL price_history.price_minor FROM existing price
-- ─────────────────────────────────────────────────────────────

UPDATE price_history
SET price_minor = CAST(ROUND(price * 100) AS INTEGER)
WHERE price IS NOT NULL AND price_minor = 0;


COMMIT;