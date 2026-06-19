"""
FlowDesk Domain Entities — Pure Python dataclasses.

These entities represent the core business concepts.
They have NO dependencies on infrastructure (no SQLAlchemy, no Flask, no Redis).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

# ─── Enums ───────────────────────────────────────────────────────────


class TicketStatus(StrEnum):
    """Lifecycle states of a support ticket."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    """Urgency level for triage and SLA tracking."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserRole(StrEnum):
    """Authorization roles within the system."""

    AGENT = "agent"
    ADMIN = "admin"
    CUSTOMER = "customer"


# ─── Value Objects / Entities ────────────────────────────────────────


@dataclass
class User:
    """A user in the FlowDesk system (agent, admin, or customer)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    full_name: str = ""
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Ticket:
    """Core business entity — a support ticket."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.MEDIUM
    tags: list[str] = field(default_factory=list)
    creator_id: str = ""
    assignee_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None

    @staticmethod
    def create(
        title: str,
        description: str,
        creator_id: str,
        priority: TicketPriority = TicketPriority.MEDIUM,
        tags: list[str] | None = None,
        assignee_id: str | None = None,
    ) -> Ticket:
        """Factory method — creates a new ticket with validated defaults."""
        now = datetime.now(UTC)
        return Ticket(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            status=TicketStatus.OPEN,
            priority=priority,
            tags=tags or [],
            creator_id=creator_id,
            assignee_id=assignee_id,
            created_at=now,
            updated_at=now,
        )

    def close(self) -> None:
        """Transition ticket to closed state."""
        self.status = TicketStatus.CLOSED
        self.closed_at = datetime.now(UTC)
        self.updated_at = self.closed_at

    def update_status(self, new_status: TicketStatus) -> None:
        """Transition to a new status with timestamp update."""
        self.status = new_status
        self.updated_at = datetime.now(UTC)
        if new_status == TicketStatus.CLOSED:
            self.closed_at = self.updated_at


@dataclass
class Comment:
    """A comment on a ticket — part of the conversation thread."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str = ""
    author_id: str = ""
    body: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Attachment:
    """A file attached to a ticket, stored in S3."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str = ""
    filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    s3_key: str = ""
    uploaded_by: str = ""
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
