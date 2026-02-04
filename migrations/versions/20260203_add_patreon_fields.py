"""20260203_add_patreon_fields

Revision ID: add_patreon_fields
Revises: 8ef04799f27f
Create Date: 2026-02-03

Add Patreon integration fields to the User table:
- patreon_id: Unique Patreon user ID
- is_patreon_supporter: Boolean flag for supporter status
- patreon_tier: Patreon membership tier (e.g., "basic", "premium")
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_patreon_fields"
down_revision = "8ef04799f27f"
branch_labels = None
depends_on = None


def upgrade():
    """Add Patreon fields to user table."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("patreon_id", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "is_patreon_supporter", sa.Boolean(), nullable=False, server_default="0"
            )
        )
        batch_op.add_column(sa.Column("patreon_tier", sa.String(), nullable=True))


def downgrade():
    """Remove Patreon fields from user table."""
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("patreon_tier")
        batch_op.drop_column("is_patreon_supporter")
        batch_op.drop_column("patreon_id")
