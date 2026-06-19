"""
Unit Tests — Update and Close Ticket Use Cases.
"""

import pytest

from app.domain.entities.ticket import Ticket, TicketPriority, TicketStatus
from app.domain.exceptions import (
    TicketAlreadyClosedError,
    TicketNotFoundError,
)
from app.domain.use_cases.close_ticket import CloseTicketUseCase
from app.domain.use_cases.update_ticket import UpdateTicketInput, UpdateTicketUseCase


class TestUpdateTicketUseCase:
    def _setup_ticket(self, repo):
        ticket = Ticket.create(
            title="Original title",
            description="Original description for the ticket.",
            creator_id="user-001",
            priority=TicketPriority.MEDIUM,
        )
        repo.save(ticket)
        return ticket

    def test_update_ticket_title_and_status(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        ticket = self._setup_ticket(mock_ticket_repo)
        uc = UpdateTicketUseCase(mock_ticket_repo, mock_search, mock_broker)
        updated = uc.execute(
            UpdateTicketInput(
                ticket_id=ticket.id, title="Updated", status="in_progress"
            )
        )
        assert updated.title == "Updated"
        assert updated.status == TicketStatus.IN_PROGRESS

    def test_update_not_found(self, mock_ticket_repo, mock_search, mock_broker):
        uc = UpdateTicketUseCase(mock_ticket_repo, mock_search, mock_broker)
        with pytest.raises(TicketNotFoundError):
            uc.execute(UpdateTicketInput(ticket_id="nope", title="X"))

    def test_update_closed_raises(self, mock_ticket_repo, mock_search, mock_broker):
        ticket = self._setup_ticket(mock_ticket_repo)
        ticket.close()
        mock_ticket_repo.update(ticket)
        uc = UpdateTicketUseCase(mock_ticket_repo, mock_search, mock_broker)
        with pytest.raises(TicketAlreadyClosedError):
            uc.execute(UpdateTicketInput(ticket_id=ticket.id, title="X"))


class TestCloseTicketUseCase:
    def test_close_success(self, mock_ticket_repo, mock_search, mock_broker):
        ticket = Ticket.create(
            title="To close", description="Will be closed.", creator_id="u1"
        )
        mock_ticket_repo.save(ticket)
        uc = CloseTicketUseCase(mock_ticket_repo, mock_search, mock_broker)
        closed = uc.execute(ticket.id)
        assert closed.status == TicketStatus.CLOSED
        assert closed.closed_at is not None

    def test_close_publishes_event(self, mock_ticket_repo, mock_search, mock_broker):
        ticket = Ticket.create(
            title="Event test", description="Closing publishes event.", creator_id="u1"
        )
        mock_ticket_repo.save(ticket)
        uc = CloseTicketUseCase(mock_ticket_repo, mock_search, mock_broker)
        uc.execute(ticket.id)
        assert len(mock_broker.published) == 1
        assert mock_broker.published[0][0] == "ticket.closed"

    def test_close_already_closed(self, mock_ticket_repo, mock_search, mock_broker):
        ticket = Ticket.create(
            title="Closed", description="Already closed ticket.", creator_id="u1"
        )
        ticket.close()
        mock_ticket_repo.save(ticket)
        uc = CloseTicketUseCase(mock_ticket_repo, mock_search, mock_broker)
        with pytest.raises(TicketAlreadyClosedError):
            uc.execute(ticket.id)

    def test_close_not_found(self, mock_ticket_repo, mock_search, mock_broker):
        uc = CloseTicketUseCase(mock_ticket_repo, mock_search, mock_broker)
        with pytest.raises(TicketNotFoundError):
            uc.execute("nope")
