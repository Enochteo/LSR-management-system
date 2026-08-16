"""Add staff review fields, alert_final_sent, and password_hash to models.

Revision ID: 2b3d4e5f6a7b
Revises: 1ad92bd63dac
Create Date: 2026-04-06 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "2b3d4e5f6a7b"
down_revision = "1ad92bd63dac"
branch_labels = None
depends_on = None


def upgrade():
    # ── students: add password_hash for admin authentication ──────── #
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("password_hash", sa.String(), nullable=True)
        )
        # Tighten is_admin to be NOT NULL (was nullable in the original schema).
        batch_op.alter_column(
            "is_admin",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        )

    # ── attendance_records: new enforcement and review columns ──────── #
    with op.batch_alter_table("attendance_records", schema=None) as batch_op:
        # One-time final expiration alert flag.
        batch_op.add_column(
            sa.Column(
                "alert_final_sent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        # Staff review fields for auto-expired sessions.
        batch_op.add_column(
            sa.Column(
                "staff_review_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("staff_reviewed_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("staff_review_notes", sa.Text(), nullable=True)
        )
        # Tighten alert_10_sent to be NOT NULL (was nullable in original schema).
        batch_op.alter_column(
            "alert_10_sent",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        )


def downgrade():
    with op.batch_alter_table("attendance_records", schema=None) as batch_op:
        batch_op.drop_column("staff_review_notes")
        batch_op.drop_column("staff_reviewed_at")
        batch_op.drop_column("staff_review_required")
        batch_op.drop_column("alert_final_sent")

    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_column("password_hash")
