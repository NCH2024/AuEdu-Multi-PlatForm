"""remove sinhvien id identity

Revision ID: 73b928f6fe57
Revises: e4331c9d7843
Create Date: 2026-05-02 18:56:25.898878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73b928f6fe57'
down_revision: Union[str, None] = 'e4331c9d7843'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
