-- Migration: vendor_location (corrected for the real Vendor schema)
-- Target: Avengers Postgres. Run by hand with psql (not Alembic).
--
-- Supersedes the earlier 20261005_vendor_location.sql. That one referenced
-- "Vendor"(id) as a bigint; the real PK is "Vendor"(vendor_id), a uuid, so that
-- migration's FK aborted the whole transaction and created nothing. Run this one
-- fresh.
--
-- Prereqs (once, as a superuser):
--     CREATE EXTENSION IF NOT EXISTS postgis;
--     CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- Both are repeated below as safe no-ops. postgis needs its package installed on
-- the box; pg_trgm you already use for vendor search.

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
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
    map_link         text,          -- optional pasted convenience link, never relied on

    -- dormant until the radius search ships; kept in sync by the trigger below
    geog             geography(Point, 4326),

    created_at       timestamp NOT NULL DEFAULT now(),
    updated_at       timestamp NOT NULL DEFAULT now(),

    -- Ghana bounding box: a bad pin never reaches the table
    CONSTRAINT vendor_location_lat_ck CHECK (latitude  BETWEEN 4.5  AND 11.2),
    CONSTRAINT vendor_location_lng_ck CHECK (longitude BETWEEN -3.3 AND 1.3)
);

-- spatial index for the future radius query (ST_DWithin). Unused by v1 reads.
CREATE INDEX IF NOT EXISTS vendor_location_geog_gix
    ON vendor_location USING GIST (geog);

-- trigram index on city: full cutover moves vendor-search city matching here
CREATE INDEX IF NOT EXISTS vendor_location_city_trgm
    ON vendor_location USING GIN (city gin_trgm_ops);

-- Keep geog derived from lat/lng so the app only ever writes lat/lng.
-- updated_at is handled by the ORM TimestampMixin on writes, so the trigger
-- only owns geog.
CREATE OR REPLACE FUNCTION vendor_location_sync() RETURNS trigger AS $$
BEGIN
    NEW.geog := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vendor_location_sync_trg ON vendor_location;
CREATE TRIGGER vendor_location_sync_trg
    BEFORE INSERT OR UPDATE ON vendor_location
    FOR EACH ROW EXECUTE FUNCTION vendor_location_sync();

COMMIT;