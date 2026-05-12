"""add username column to user

Revision ID: 23aeea3270d6
Revises: 7bbe54054d85
Create Date: 2026-05-12 01:56:55.652910

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23aeea3270d6'
down_revision: Union[str, None] = '7bbe54054d85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('username', sa.String(length=100), nullable=True))
    op.execute("""
        UPDATE "user"
        SET username = split_part(email, '@', 1) || '_' || id
        WHERE username IS NULL
    """)
    op.alter_column('user', 'username', nullable=False)
    op.create_unique_constraint('uq_user_username', 'user', ['username'])
    op.create_index('ix_user_username', 'user', ['username'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_username', table_name='user')
    op.drop_constraint('uq_user_username', 'user', type_='unique')
    op.drop_column('user', 'username')
