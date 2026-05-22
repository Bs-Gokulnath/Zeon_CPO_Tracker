"""Add content_hash column to stations for incremental ETL detection.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE stations
        ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)
    """)
    # Index so the ETL's WHERE content_hash IS DISTINCT FROM can use it
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_stations_content_hash
            ON stations (content_hash)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_stations_content_hash")
    op.execute("ALTER TABLE stations DROP COLUMN IF EXISTS content_hash")
