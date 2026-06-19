"""
Use Case: Close Ticket

Transitions a ticket to CLOSED status and publishes a closure event.
"""

from __future__ import annotations

from app.domain.entities.ticket import Ticket, TicketStatus
from app.domain.exceptions import TicketAlreadyClosedError, TicketNotFoundError
from app.domain.ports.repositories import (
    MessageBroker,
    SearchPort,
    TicketRepository,
)


class CloseTicketUseCase:
    """Closes a ticket, updates search index, and publishes closure event."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        search: SearchPort,
        broker: MessageBroker,
    ):
        self._repo = ticket_repo
        self._search = search
        self._broker = broker

    def execute(self, ticket_id: str) -> Ticket:
        ticket = self._repo.get_by_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(ticket_id)

        if ticket.status == TicketStatus.CLOSED:
            raise TicketAlreadyClosedError(ticket_id)

        ticket.close()
        updated_ticket = self._repo.update(ticket)

        try:
            self._search.index_ticket(updated_ticket)
        except Exception:
            pass

        try:
            self._broker.publish(
                "ticket.closed",
                {
                    "ticket_id": updated_ticket.id,
                    "closed_at": updated_ticket.closed_at.isoformat()
                    if updated_ticket.closed_at
                    else None,
                    "creator_id": updated_ticket.creator_id,
                },
            )
        except Exception:
            pass

        return updated_ticket
