"""rename company.user_id to admin_user_id

Revision ID: 7bbe54054d85
Revises: 6ec006f331aa
Create Date: 2026-05-11 23:14:23.003229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bbe54054d85'
down_revision: Union[str, None] = '6ec006f331aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.alter_column('company', 'user_id', new_column_name='admin_user_id')


def downgrade() -> None:
    op.alter_column('company', 'admin_user_id', new_column_name='user_id')