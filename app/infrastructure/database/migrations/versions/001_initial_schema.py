"""Initial schema — users, tickets, comments, attachments

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Users table ──
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("agent", "admin", "customer", name="user_role_enum"),
            nullable=False,
            server_default="customer",
        ),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])

    # ── Tickets table ──
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_progress",
                "waiting_on_customer",
                "resolved",
                "closed",
                name="ticket_status_enum",
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "critical", name="ticket_priority_enum"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("tags", ARRAY(sa.String(100)), nullable=False, server_default="{}"),
        sa.Column(
            "creator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "assignee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_tickets_status", "tickets", ["status"])
    op.create_index("idx_tickets_priority", "tickets", ["priority"])
    op.create_index("idx_tickets_creator", "tickets", ["creator_id"])
    op.create_index("idx_tickets_assignee", "tickets", ["assignee_id"])
    op.create_index("idx_tickets_created_at", "tickets", ["created_at"])
    op.create_index("idx_tickets_status_priority", "tickets", ["status", "priority"])

    # ── Comments table ──
    op.create_table(
        "comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.String(36),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_comments_ticket", "comments", ["ticket_id"])
    op.create_index("idx_comments_created_at", "comments", ["created_at"])

    # ── Attachments table ──
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "ticket_id",
            sa.String(36),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("s3_key", sa.String(1000), nullable=False, unique=True),
        sa.Column(
            "uploaded_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_attachments_ticket", "attachments", ["ticket_id"])


def downgrade() -> None:
    op.drop_table("attachments")
    op.drop_table("comments")
    op.drop_table("tickets")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS ticket_priority_enum")
    op.execute("DROP TYPE IF EXISTS ticket_status_enum")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
