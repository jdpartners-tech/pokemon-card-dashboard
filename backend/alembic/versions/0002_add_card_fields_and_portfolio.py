"""add card fields and portfolio_items

Revision ID: 0002
Revises: 87fe7d11e185
Create Date: 2026-05-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: Union[str, None] = '87fe7d11e185'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cards', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('accent_color', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('snkrdunk_url', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('pricecharting_url', sa.String(), nullable=True))
    op.add_column('cards', sa.Column('psa_population', sa.Integer(), nullable=True))
    op.add_column('cards', sa.Column('sales_per_day', sa.Numeric(8, 2), nullable=True))

    op.create_table(
        'portfolio_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('card_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('cards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purchase_price_hkd', sa.Numeric(12, 2), nullable=False),
        sa.Column('purchased_at', sa.Date(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('portfolio_items')
    for col in ['sales_per_day', 'psa_population', 'pricecharting_url',
                'snkrdunk_url', 'accent_color', 'image_url']:
        op.drop_column('cards', col)
