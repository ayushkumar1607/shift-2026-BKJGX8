"""Expose default credential availability in the synthetic profile registry."""

import sqlalchemy as sa
from alembic import op

revision = "0003_default_credential_status"
down_revision = "0002_rotation_state_history"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("device_profiles")}
    if "default_credential_status" not in columns:
        op.add_column(
            "device_profiles",
            sa.Column(
                "default_credential_status",
                sa.String(length=80),
                nullable=False,
                server_default=sa.text("'Demo credential available'"),
            ),
        )


def downgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("device_profiles")}
    if "default_credential_status" in columns:
        op.drop_column("device_profiles", "default_credential_status")
