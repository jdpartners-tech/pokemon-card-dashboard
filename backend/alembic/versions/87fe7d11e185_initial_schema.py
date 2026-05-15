"""initial schema

Revision ID: 87fe7d11e185
Revises: 
Create Date: 2026-05-12 00:51:35.995866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '87fe7d11e185'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('set_name', sa.String(), nullable=False),
        sa.Column('card_number', sa.String(), nullable=True),
        sa.Column('snkrdunk_id', sa.String(), nullable=True, unique=True),
        sa.Column('pricecharting_id', sa.String(), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'price_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snkrdunk_price_hkd', sa.Numeric(12, 2), nullable=True),
        sa.Column('pricecharting_price_usd', sa.Numeric(12, 2), nullable=True),
        sa.Column('pricecharting_price_hkd', sa.Numeric(12, 2), nullable=True),
        sa.Column('usd_to_hkd_rate', sa.Numeric(10, 4), nullable=True),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'watchlist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('watchlist')
    op.drop_table('price_snapshots')
    op.drop_table('cards')
