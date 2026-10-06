-- Migration: vendor_location (v1, no PostGIS)
-- Target: Avengers Postgres. Run by hand with psql.
--
-- Use this INSTEAD of the postgis version for now. The geography column, its
-- GiST index, and the sync trigger were only for the future radius search and
-- are omitted here. v1 runs entirely on latitude/longitude. When you build the
-- radius search, a follow-up migration adds PostGIS, the geog column + GiST
-- index + trigger, and backfills geog for existing rows.
--
-- pg_trgm is already enabled on this database; the city index below needs it.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS vendor_location (
    -- one row per vendor; vendor_id is the natural primary key
    vendor_id        uuid PRIMARY KEY
                        REFERENCES "Vendor"(vendor_id) ON DELETE CASCADE,

    latitude         double precision NOT NULL,
    longitude        double precision NOT NULL,

    address_line1    text,
    city             text,
    region           text,
    country          text NOT NULL DEFAULT 'Ghana',
    digital_address  text,          -- GhanaPost GPS, e.g. GA-123-4567
    map_link         text,          -- optional pasted convenience link

    created_at       timestamp NOT NULL DEFAULT now(),
    updated_at       timestamp NOT NULL DEFAULT now(),

    -- Ghana bounding box: a bad pin never reaches the table
    CONSTRAINT vendor_location_lat_ck CHECK (latitude  BETWEEN 4.5  AND 11.2),
    CONSTRAINT vendor_location_lng_ck CHECK (longitude BETWEEN -3.3 AND 1.3)
);

-- trigram index on city for vendor search (full cutover sources city here)
CREATE INDEX IF NOT EXISTS vendor_location_city_trgm
    ON vendor_location USING GIN (city gin_trgm_ops);

COMMIT;