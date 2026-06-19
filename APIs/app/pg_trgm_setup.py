"""
Ensure the pg_trgm extension exists BEFORE create_all() builds the trigram GIN
indexes. SQLAlchemy's create_all does NOT create extensions, so without this a
fresh DB fails with: "operator class gin_trgm_ops does not exist".

USAGE — two options:

(A) One-liner before create_all (simplest). Wherever you call
    Base.metadata.create_all(bind=engine), do this first:

        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        Base.metadata.create_all(bind=engine)

(B) Auto via an event listener (set-and-forget). Import this module once at
    startup (e.g. in the same place you import your models / call create_all)
    AFTER you've created `engine` and `Base`. Call:

        from app.config.db.pg_trgm_setup import register_pg_trgm
        register_pg_trgm(Base, engine)

    It hooks Base.metadata 'before_create' so the extension is guaranteed to
    exist the moment tables/indexes are built.
"""

from sqlalchemy import event, text


def register_pg_trgm(base, engine) -> None:
    """Create pg_trgm just before this metadata's tables are created."""

    @event.listens_for(base.metadata, "before_create")
    def _create_pg_trgm(target, connection, **kw):
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    # If create_all already ran in this process, ensure it exists now too.
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    except Exception:
        # Safe to ignore here; the before_create hook will still run on create_all.
        pass