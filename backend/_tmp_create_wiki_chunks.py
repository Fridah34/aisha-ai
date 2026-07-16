import asyncio

from app.database import async_session_factory
from sqlalchemy import text

STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
    """
    CREATE TABLE wiki_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        business_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        source_file VARCHAR(255) NOT NULL,
        section_path VARCHAR(500) NOT NULL DEFAULT '',
        chunk_text TEXT NOT NULL,
        content_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_wiki_chunk_hash UNIQUE (business_id, content_hash),
        CONSTRAINT chk_wiki_chunks_text_not_empty CHECK (char_length(chunk_text) > 0),
        CONSTRAINT chk_wiki_chunks_hash_not_empty CHECK (content_hash <> '')
    );
    """,
    """
    ALTER TABLE wiki_chunks
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('simple', chunk_text)) STORED;
    """,
    "CREATE INDEX ix_wiki_chunks_search_vector ON wiki_chunks USING gin (search_vector);",
    "CREATE INDEX ix_wiki_chunks_business_id ON wiki_chunks (business_id);",
    "CREATE INDEX ix_wiki_chunks_business_source ON wiki_chunks (business_id, source_file);",
    """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """,
    """
    CREATE TRIGGER update_wiki_chunks_updated_at
    BEFORE UPDATE ON wiki_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
    """,
    "ALTER TABLE wiki_chunks ENABLE ROW LEVEL SECURITY;",
    "ALTER TABLE wiki_chunks FORCE ROW LEVEL SECURITY;",
    """
    CREATE POLICY tenant_isolation_wiki_chunks ON wiki_chunks
    USING (business_id = current_setting('app.current_tenant_id', true)::uuid);
    """,
]


async def main() -> None:
    async with async_session_factory() as session:
        for stmt in STATEMENTS:
            await session.execute(text(stmt))
        await session.commit()
    print("wiki_chunks table created successfully")


asyncio.run(main())
