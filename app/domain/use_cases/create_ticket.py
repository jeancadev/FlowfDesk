"""
Use Case: Create Ticket

Orchestrates ticket creation with event publishing and search indexing.
Pure business logic — no Flask, no SQLAlchemy, just Python.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.ticket import Ticket, TicketPriority
from app.domain.exceptions import InvalidTicketDataError
from app.domain.ports.repositories import (
    MessageBroker,
    SearchPort,
    TicketRepository,
)


@dataclass
class CreateTicketInput:
    """Input DTO for creating a ticket."""

    title: str
    description: str
    creator_id: str
    priority: str = "medium"
    tags: list[str] | None = None
    assignee_id: str | None = None


class CreateTicketUseCase:
    """Creates a ticket, persists it, indexes it for search, and publishes an event."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        search: SearchPort,
        broker: MessageBroker,
    ):
        self._repo = ticket_repo
        self._search = search
        self._broker = broker

    def execute(self, input_data: CreateTicketInput) -> Ticket:
        # ── Validation ──
        if not input_data.title or len(input_data.title.strip()) < 3:
            raise InvalidTicketDataError("Title must be at least 3 characters")
        if not input_data.description or len(input_data.description.strip()) < 10:
            raise InvalidTicketDataError("Description must be at least 10 characters")

        # ── Create domain entity ──
        try:
            priority = TicketPriority(input_data.priority)
        except ValueError:
            raise InvalidTicketDataError(
                f"Invalid priority: {input_data.priority}. "
                f"Must be one of: {[p.value for p in TicketPriority]}"
            ) from None

        ticket = Ticket.create(
            title=input_data.title.strip(),
            description=input_data.description.strip(),
            creator_id=input_data.creator_id,
            priority=priority,
            tags=input_data.tags,
            assignee_id=input_data.assignee_id,
        )

        # ── Persist ──
        saved_ticket = self._repo.save(ticket)

        # ── Index for search ──
        try:
            self._search.index_ticket(saved_ticket)
        except Exception:
            pass  # Search indexing is non-critical; ticket is already persisted

        # ── Publish event ──
        try:
            self._broker.publish(
                "ticket.created",
                {
                    "ticket_id": saved_ticket.id,
                    "title": saved_ticket.title,
                    "creator_id": saved_ticket.creator_id,
                    "priority": saved_ticket.priority.value,
                    "status": saved_ticket.status.value,
                    "created_at": saved_ticket.created_at.isoformat(),
                },
            )
        except Exception:
            pass  # Event publishing is non-critical

        return saved_ticket
