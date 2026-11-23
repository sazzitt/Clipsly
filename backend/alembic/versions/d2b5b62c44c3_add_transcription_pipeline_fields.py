"""add_transcription_pipeline_fields

Revision ID: d2b5b62c44c3
Revises: 05adc4b773ff
Create Date: 2026-11-23 21:44:21.530609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2b5b62c44c3'
down_revision: Union[str, Sequence[str], None] = '05adc4b773ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('transcript_segments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('no_speech_prob', sa.Float(), nullable=True))

    with op.batch_alter_table('transcripts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('audio_asset_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('device', sa.String(length=16), server_default='cuda', nullable=False))
        batch_op.add_column(sa.Column('language_probability', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=32), server_default='COMPLETED', nullable=False))
        batch_op.add_column(sa.Column('segment_count', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('audio_duration_seconds', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))
        batch_op.create_index('idx_transcripts_audio_asset_id', ['audio_asset_id'], unique=False)
        batch_op.create_index('idx_transcripts_status', ['status'], unique=False)
        batch_op.create_foreign_key('fk_transcripts_audio_asset_id', 'audio_assets', ['audio_asset_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('transcripts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_transcripts_audio_asset_id', type_='foreignkey')
        batch_op.drop_index('idx_transcripts_status')
        batch_op.drop_index('idx_transcripts_audio_asset_id')
        batch_op.drop_column('error_message')
        batch_op.drop_column('audio_duration_seconds')
        batch_op.drop_column('segment_count')
        batch_op.drop_column('status')
        batch_op.drop_column('language_probability')
        batch_op.drop_column('device')
        batch_op.drop_column('audio_asset_id')

    with op.batch_alter_table('transcript_segments', schema=None) as batch_op:
        batch_op.drop_column('no_speech_prob')
