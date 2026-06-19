"""
Use Case: Update Ticket

Handles status transitions, field updates, and publishes change events.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.ticket import Ticket, TicketPriority, TicketStatus
from app.domain.exceptions import (
    InvalidTicketDataError,
    TicketAlreadyClosedError,
    TicketNotFoundError,
)
from app.domain.ports.repositories import (
    MessageBroker,
    SearchPort,
    TicketRepository,
)


@dataclass
class UpdateTicketInput:
    """Input DTO for updating a ticket."""

    ticket_id: str
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    tags: list[str] | None = None
    assignee_id: str | None = None


class UpdateTicketUseCase:
    """Updates a ticket's fields, re-indexes, and publishes an update event."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        search: SearchPort,
        broker: MessageBroker,
    ):
        self._repo = ticket_repo
        self._search = search
        self._broker = broker

    def execute(self, input_data: UpdateTicketInput) -> Ticket:
        # ── Fetch existing ──
        ticket = self._repo.get_by_id(input_data.ticket_id)
        if ticket is None:
            raise TicketNotFoundError(input_data.ticket_id)

        if ticket.status == TicketStatus.CLOSED:
            raise TicketAlreadyClosedError(input_data.ticket_id)

        # ── Apply changes ──
        changes: dict[str, str] = {}

        if input_data.title is not None:
            if len(input_data.title.strip()) < 3:
                raise InvalidTicketDataError("Title must be at least 3 characters")
            changes["title"] = f"{ticket.title} → {input_data.title}"
            ticket.title = input_data.title.strip()

        if input_data.description is not None:
            changes["description"] = "updated"
            ticket.description = input_data.description.strip()

        if input_data.status is not None:
            try:
                new_status = TicketStatus(input_data.status)
            except ValueError:
                raise InvalidTicketDataError(
                    f"Invalid status: {input_data.status}. "
                    f"Must be one of: {[s.value for s in TicketStatus]}"
                ) from None
            changes["status"] = f"{ticket.status.value} → {new_status.value}"
            ticket.update_status(new_status)

        if input_data.priority is not None:
            try:
                new_priority = TicketPriority(input_data.priority)
            except ValueError:
                raise InvalidTicketDataError(
                    f"Invalid priority: {input_data.priority}. "
                    f"Must be one of: {[p.value for p in TicketPriority]}"
                ) from None
            changes["priority"] = f"{ticket.priority.value} → {new_priority.value}"
            ticket.priority = new_priority

        if input_data.tags is not None:
            changes["tags"] = f"{ticket.tags} → {input_data.tags}"
            ticket.tags = input_data.tags

        if input_data.assignee_id is not None:
            changes["assignee_id"] = f"{ticket.assignee_id} → {input_data.assignee_id}"
            ticket.assignee_id = input_data.assignee_id

        # ── Persist ──
        updated_ticket = self._repo.update(ticket)

        # ── Re-index ──
        try:
            self._search.index_ticket(updated_ticket)
        except Exception:
            pass

        # ── Publish event ──
        try:
            self._broker.publish(
                "ticket.updated",
                {
                    "ticket_id": updated_ticket.id,
                    "changes": changes,
                    "updated_at": updated_ticket.updated_at.isoformat(),
                },
            )
        except Exception:
            pass

        return updated_ticket
