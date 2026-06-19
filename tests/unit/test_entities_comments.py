"""Unit Tests — Add Comment and Domain Entities."""

import pytest

from app.domain.entities.ticket import Ticket, TicketPriority, TicketStatus
from app.domain.exceptions import (
    InvalidTicketDataError,
    TicketAlreadyClosedError,
    TicketNotFoundError,
)
from app.domain.use_cases.add_comment import AddCommentInput, AddCommentUseCase


class TestTicketEntity:
    def test_create_ticket_factory(self):
        ticket = Ticket.create(
            title="Test", description="Description here", creator_id="u1"
        )
        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == TicketPriority.MEDIUM
        assert ticket.id is not None

    def test_close_ticket(self):
        ticket = Ticket.create(
            title="Test", description="Description here", creator_id="u1"
        )
        ticket.close()
        assert ticket.status == TicketStatus.CLOSED
        assert ticket.closed_at is not None

    def test_update_status(self):
        ticket = Ticket.create(
            title="Test", description="Description here", creator_id="u1"
        )
        ticket.update_status(TicketStatus.IN_PROGRESS)
        assert ticket.status == TicketStatus.IN_PROGRESS


class TestAddCommentUseCase:
    def test_add_comment_success(self, mock_ticket_repo, mock_comment_repo):
        ticket = Ticket.create(
            title="Test ticket", description="Description here.", creator_id="u1"
        )
        mock_ticket_repo.save(ticket)
        uc = AddCommentUseCase(mock_ticket_repo, mock_comment_repo)
        comment = uc.execute(
            AddCommentInput(ticket_id=ticket.id, author_id="u2", body="Looks good!")
        )
        assert comment.body == "Looks good!"
        assert comment.ticket_id == ticket.id

    def test_add_comment_ticket_not_found(self, mock_ticket_repo, mock_comment_repo):
        uc = AddCommentUseCase(mock_ticket_repo, mock_comment_repo)
        with pytest.raises(TicketNotFoundError):
            uc.execute(AddCommentInput(ticket_id="nope", author_id="u1", body="Hello"))

    def test_add_comment_on_closed_ticket(self, mock_ticket_repo, mock_comment_repo):
        ticket = Ticket.create(
            title="Closed", description="Closed ticket.", creator_id="u1"
        )
        ticket.close()
        mock_ticket_repo.save(ticket)
        uc = AddCommentUseCase(mock_ticket_repo, mock_comment_repo)
        with pytest.raises(TicketAlreadyClosedError):
            uc.execute(AddCommentInput(ticket_id=ticket.id, author_id="u1", body="Hi"))

    def test_add_comment_empty_body(self, mock_ticket_repo, mock_comment_repo):
        ticket = Ticket.create(
            title="Test", description="Description here.", creator_id="u1"
        )
        mock_ticket_repo.save(ticket)
        uc = AddCommentUseCase(mock_ticket_repo, mock_comment_repo)
        with pytest.raises(InvalidTicketDataError):
            uc.execute(AddCommentInput(ticket_id=ticket.id, author_id="u1", body=""))
