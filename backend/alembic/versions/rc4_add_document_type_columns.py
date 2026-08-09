"""add_document_type_and_topic_columns_for_rc4

Revision ID: rc4_activation_001
Revises: 9fc08ce30485
Create Date: 2026-08-02 05:16:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'rc4_activation_001'
down_revision: Union[str, Sequence[str], None] = '9fc08ce30485'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to processed_articles
    op.add_column('processed_articles', sa.Column('document_type', sa.String(length=50), nullable=True))
    op.add_column('processed_articles', sa.Column('is_multi_topic', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('processed_articles', sa.Column('primary_topics', sa.JSON(), nullable=True))
    op.add_column('processed_articles', sa.Column('dominant_topic_percentage', sa.Numeric(), nullable=True))
    
    op.create_index(op.f('ix_processed_articles_document_type'), 'processed_articles', ['document_type'], unique=False)

    # 2. Add columns to articles (read model)
    op.add_column('articles', sa.Column('document_type', sa.String(length=50), nullable=True))
    op.add_column('articles', sa.Column('is_multi_topic', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('articles', sa.Column('primary_topics', sa.JSON(), nullable=True))
    op.add_column('articles', sa.Column('dominant_topic_percentage', sa.Numeric(), nullable=True))

    op.create_index(op.f('ix_articles_document_type'), 'articles', ['document_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_articles_document_type'), table_name='articles')
    op.drop_column('articles', 'dominant_topic_percentage')
    op.drop_column('articles', 'primary_topics')
    op.drop_column('articles', 'is_multi_topic')
    op.drop_column('articles', 'document_type')

    op.drop_index(op.f('ix_processed_articles_document_type'), table_name='processed_articles')
    op.drop_column('processed_articles', 'dominant_topic_percentage')
    op.drop_column('processed_articles', 'primary_topics')
    op.drop_column('processed_articles', 'is_multi_topic')
    op.drop_column('processed_articles', 'document_type')
