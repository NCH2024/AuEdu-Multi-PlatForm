"""Fix HocPhan ID auto increment (IDENTITY)

Revision ID: a1b2c3d4e5f6
Revises: 67f2346d768b
Create Date: 2026-07-01 10:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '67f2346d768b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bước 1: Thêm GENERATED ALWAYS AS IDENTITY cho cột id bảng hocphan
    # (Đã chạy rồi, bọc trong try/except để idempotent)
    try:
        op.execute('ALTER TABLE hocphan ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY')
    except Exception:
        pass

    # Bước 2: Đồng bộ sequence với max id hiện tại để tránh trùng lặp
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('hocphan', 'id'),
            COALESCE((SELECT MAX(id) FROM hocphan), 0) + 1,
            false
        )
    """)


def downgrade() -> None:
    # PostgreSQL không hỗ trợ DROP IDENTITY trực tiếp trên một số phiên bản cũ
    op.execute('ALTER TABLE hocphan ALTER COLUMN id DROP IDENTITY IF EXISTS')
