"""add_highlight_intelligence_fields

Revision ID: 6422c6335aad
Revises: d2b5b62c44c3
Create Date: 2026-11-24 00:15:26.156828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6422c6335aad'
down_revision: Union[str, Sequence[str], None] = 'd2b5b62c44c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('highlights', schema=None) as batch_op:
        batch_op.add_column(sa.Column('scoring_version', sa.String(length=16), server_default='v1', nullable=False))
        batch_op.add_column(sa.Column('rank', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('explanation', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('transcript_excerpt', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('warnings_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('detection_metadata_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.create_index('idx_highlights_transcript_id', ['transcript_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('highlights', schema=None) as batch_op:
        batch_op.drop_index('idx_highlights_transcript_id')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('detection_metadata_json')
        batch_op.drop_column('warnings_json')
        batch_op.drop_column('transcript_excerpt')
        batch_op.drop_column('explanation')
        batch_op.drop_column('rank')
        batch_op.drop_column('scoring_version')
