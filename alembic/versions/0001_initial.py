"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-04-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    op.create_table(
        'articles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('original_url', sa.String(length=1000), nullable=False),
        sa.Column('short_code', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('article_text', sa.Text(), nullable=False),
        sa.Column('image', sa.String(length=1000), nullable=True),
        sa.Column('slug', sa.String(length=500), nullable=False),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('english_summary', sa.Text(), nullable=False),
        sa.Column('original_summary', sa.Text(), nullable=False),
        sa.Column('source_language', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_articles_short_code', 'articles', ['short_code'], unique=True)
    op.create_index('ix_articles_original_url', 'articles', ['original_url'], unique=False)
    op.create_index('ix_articles_user_id', 'articles', ['user_id'], unique=False)
    op.create_index('ix_articles_created_at', 'articles', ['created_at'], unique=False)

    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('prefix', sa.String(length=16), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_api_keys_prefix', 'api_keys', ['prefix'], unique=False)
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_api_keys_user_id', table_name='api_keys')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_prefix', table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_index('ix_articles_created_at', table_name='articles')
    op.drop_index('ix_articles_user_id', table_name='articles')
    op.drop_index('ix_articles_original_url', table_name='articles')
    op.drop_index('ix_articles_short_code', table_name='articles')
    op.drop_table('articles')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
