"""
SQLAlchemy ORM Models — PostgreSQL schema definition.

These models map domain entities to database tables.
They include proper indexes, constraints, and relationships
for query optimization.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base


class UserModel(Base):
    """ORM model for users table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("agent", "admin", "customer", name="user_role_enum"),
        nullable=False,
        default="customer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    created_tickets: Mapped[list["TicketModel"]] = relationship(
        "TicketModel",
        foreign_keys="TicketModel.creator_id",
        back_populates="creator",
    )
    assigned_tickets: Mapped[list["TicketModel"]] = relationship(
        "TicketModel",
        foreign_keys="TicketModel.assignee_id",
        back_populates="assignee",
    )

    # Indexes for query optimization
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
    )


class TicketModel(Base):
    """ORM model for tickets table."""

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "open",
            "in_progress",
            "waiting_on_customer",
            "resolved",
            "closed",
            name="ticket_status_enum",
        ),
        nullable=False,
        default="open",
    )
    priority: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="ticket_priority_enum"),
        nullable=False,
        default="medium",
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        default=list,
        nullable=False,
    )
    creator_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
    assignee_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    creator: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys=[creator_id],
        back_populates="created_tickets",
    )
    assignee: Mapped["UserModel | None"] = relationship(
        "UserModel",
        foreign_keys=[assignee_id],
        back_populates="assigned_tickets",
    )
    comments: Mapped[list["CommentModel"]] = relationship(
        "CommentModel",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["AttachmentModel"]] = relationship(
        "AttachmentModel",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )

    # Indexes for query optimization
    __table_args__ = (
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_priority", "priority"),
        Index("idx_tickets_creator", "creator_id"),
        Index("idx_tickets_assignee", "assignee_id"),
        Index("idx_tickets_created_at", "created_at"),
        Index("idx_tickets_status_priority", "status", "priority"),
    )


class CommentModel(Base):
    """ORM model for comments table."""

    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    ticket: Mapped["TicketModel"] = relationship(
        "TicketModel", back_populates="comments"
    )
    author: Mapped["UserModel"] = relationship("UserModel")

    __table_args__ = (
        Index("idx_comments_ticket", "ticket_id"),
        Index("idx_comments_created_at", "created_at"),
    )


class AttachmentModel(Base):
    """ORM model for attachments table."""

    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    uploaded_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    ticket: Mapped["TicketModel"] = relationship(
        "TicketModel", back_populates="attachments"
    )
    uploader: Mapped["UserModel"] = relationship("UserModel")

    __table_args__ = (Index("idx_attachments_ticket", "ticket_id"),)
