"""Persist the backend credential rotation state sequence."""

import sqlalchemy as sa
from alembic import op

revision = "0002_rotation_state_history"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("credential_rotations")}
    if "state_history" not in columns:
        op.add_column("credential_rotations", sa.Column("state_history", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("credential_rotations")}
    if "state_history" in columns:
        op.drop_column("credential_rotations", "state_history")

