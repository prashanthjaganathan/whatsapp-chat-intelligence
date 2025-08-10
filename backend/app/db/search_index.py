from sqlalchemy import text
from sqlalchemy.engine import Engine

DDL_CREATE_TSV_COLUMN = """
ALTER TABLE IF EXISTS messages
    ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
"""

DDL_CREATE_TSV_INDEX = """
CREATE INDEX IF NOT EXISTS idx_messages_content_tsv
ON messages USING GIN (content_tsv);
"""

DDL_CREATE_GROUP_CONTENT_HASH_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_group_contenthash
ON messages (group_id, content_hash)
WHERE content_hash IS NOT NULL;
"""

DDL_ADD_DEDUP_COLUMNS = """
ALTER TABLE IF EXISTS messages
    ADD COLUMN IF NOT EXISTS content_hash text,
    ADD COLUMN IF NOT EXISTS first_seen timestamptz DEFAULT now(),
    ADD COLUMN IF NOT EXISTS last_seen timestamptz DEFAULT now(),
    ADD COLUMN IF NOT EXISTS occurrence_count integer DEFAULT 1;
"""

DDL_CREATE_CANONICAL = """
CREATE TABLE IF NOT EXISTS canonical_messages (
    content_hash text PRIMARY KEY,
    content text,
    first_seen timestamptz DEFAULT now(),
    last_seen timestamptz DEFAULT now(),
    occurrence_total integer DEFAULT 1,
    groups_seen text[] DEFAULT ARRAY[]::text[]
);
"""

def ensure_postgres_full_text_search(engine: Engine) -> None:
    """Ensure Postgres full-text search column and index exist for messages.content.
    Safe to run multiple times.
    """
    with engine.connect() as conn:
        conn.execute(text(DDL_CREATE_TSV_COLUMN))
        conn.execute(text(DDL_CREATE_TSV_INDEX))
        conn.execute(text(DDL_ADD_DEDUP_COLUMNS))
        conn.execute(text(DDL_CREATE_GROUP_CONTENT_HASH_INDEX))
        conn.execute(text(DDL_CREATE_CANONICAL))
        conn.commit()
