"""
FlowDesk Domain Ports — Interfaces the domain depends on.

These are Protocol classes (structural subtyping). The domain declares
WHAT it needs; infrastructure provides HOW.

This is the "D" in SOLID: Dependency Inversion.
The domain never imports from infrastructure. Infrastructure implements these.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.entities.ticket import Attachment, Comment, Ticket, User

# ─── Repository Ports ────────────────────────────────────────────────


class TicketRepository(Protocol):
    """Port for ticket persistence operations."""

    def save(self, ticket: Ticket) -> Ticket: ...

    def get_by_id(self, ticket_id: str) -> Ticket | None: ...

    def list_all(
        self,
        status: str | None = None,
        assignee_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Ticket]: ...

    def update(self, ticket: Ticket) -> Ticket: ...

    def delete(self, ticket_id: str) -> bool: ...

    def count(
        self,
        status: str | None = None,
        assignee_id: str | None = None,
    ) -> int: ...


class UserRepository(Protocol):
    """Port for user persistence operations."""

    def save(self, user: User) -> User: ...

    def get_by_id(self, user_id: str) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def list_all(self, limit: int = 50, offset: int = 0) -> list[User]: ...


class CommentRepository(Protocol):
    """Port for comment persistence."""

    def save(self, comment: Comment) -> Comment: ...

    def get_by_ticket_id(self, ticket_id: str) -> list[Comment]: ...


class AttachmentRepository(Protocol):
    """Port for attachment metadata persistence."""

    def save(self, attachment: Attachment) -> Attachment: ...

    def get_by_ticket_id(self, ticket_id: str) -> list[Attachment]: ...


# ─── Infrastructure Ports ────────────────────────────────────────────


class SearchPort(Protocol):
    """Port for full-text search engine (Elasticsearch)."""

    def index_ticket(self, ticket: Ticket) -> None: ...

    def search_tickets(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]: ...

    def delete_ticket(self, ticket_id: str) -> None: ...


class CachePort(Protocol):
    """Port for caching layer (Redis)."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None: ...

    def delete(self, key: str) -> None: ...

    def increment(self, key: str, ttl_seconds: int = 60) -> int: ...


class MessageBroker(Protocol):
    """Port for event publishing (Kafka)."""

    def publish(self, topic: str, message: dict[str, Any]) -> None: ...

    def close(self) -> None: ...


class StoragePort(Protocol):
    """Port for file storage (S3)."""

    def upload(
        self,
        file_data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str: ...

    def get_presigned_url(self, key: str, expiration: int = 3600) -> str: ...

    def delete(self, key: str) -> None: ...
