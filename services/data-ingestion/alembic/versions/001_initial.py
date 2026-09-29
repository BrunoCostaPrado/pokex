"""Initial migration

Revision ID: 001
Revises:
Create Date: 2025-09-21 23:16:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sets table
    op.create_table(
        'sets',
        sa.Column('id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('series', sa.String(100), nullable=True),
        sa.Column('release_date', sa.DateTime(), nullable=True),
        sa.Column('total_cards', sa.Integer(), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('symbol_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create cards table
    op.create_table(
        'cards',
        sa.Column('id', sa.String(100), nullable=False),
        sa.Column('set_id', sa.String(50), nullable=False),
        sa.Column('number', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('rarity', sa.String(50), nullable=True),
        sa.Column('hp', sa.Integer(), nullable=True),
        sa.Column('types', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('subtypes', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('supertype', sa.String(50), nullable=True),
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tcgplayer_url', sa.String(500), nullable=True),
        sa.Column('cardmarket_url', sa.String(500), nullable=True),
        sa.Column('prices', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['set_id'], ['sets.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cards_set_id', 'cards', ['set_id'])
    op.create_index('ix_cards_name', 'cards', ['name'])

    # Create prices table
    op.create_table(
        'prices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('card_id', sa.String(100), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['card_id'], ['cards.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prices_card_id', 'prices', ['card_id'])
    op.create_index('ix_prices_source', 'prices', ['source'])


def downgrade() -> None:
    op.drop_index('ix_prices_source', table_name='prices')
    op.drop_index('ix_prices_card_id', table_name='prices')
    op.drop_table('prices')
    op.drop_index('ix_cards_name', table_name='cards')
    op.drop_index('ix_cards_set_id', table_name='cards')
    op.drop_table('cards')
    op.drop_table('sets')