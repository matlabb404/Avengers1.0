-- Migration: drop address columns from "Vendor" (full cutover to vendor_location)
-- Target: Avengers Postgres. Run by hand with psql (not Alembic).
--
-- RUN ORDER: apply this LAST, after the code that no longer reads these columns
-- is deployed. Running it earlier would 500 any request that still reads city or
-- country.
--
-- city is referenced by the generated search_tsv column and the vendor_city_trgm
-- index, so both are dropped first, the columns go, then search_tsv is rebuilt
-- without city (business_name A, first/last name B).

BEGIN;

-- 1. drop the city trigram index and the generated search vector that uses city
--    (dropping search_tsv also drops its dependent index vendor_search_tsv_gin)
DROP INDEX IF EXISTS vendor_city_trgm;
ALTER TABLE "Vendor" DROP COLUMN IF EXISTS search_tsv;

-- 2. drop the address columns (now sourced from vendor_location)
ALTER TABLE "Vendor"
    DROP COLUMN IF EXISTS house_no,
    DROP COLUMN IF EXISTS street,
    DROP COLUMN IF EXISTS city,
    DROP COLUMN IF EXISTS state,
    DROP COLUMN IF EXISTS postal_code,
    DROP COLUMN IF EXISTS country;

-- 3. rebuild the full-text vector without city
ALTER TABLE "Vendor" ADD COLUMN search_tsv tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(business_name, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(first_name,    '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(last_name,     '')), 'B')
    ) STORED;

CREATE INDEX IF NOT EXISTS vendor_search_tsv_gin
    ON "Vendor" USING gin (search_tsv);

COMMIT;
