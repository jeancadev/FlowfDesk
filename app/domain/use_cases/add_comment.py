"""
Use Case: Add Comment

Adds a comment to an existing ticket's conversation thread.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.ticket import Comment, TicketStatus
from app.domain.exceptions import (
    InvalidTicketDataError,
    TicketAlreadyClosedError,
    TicketNotFoundError,
)
from app.domain.ports.repositories import CommentRepository, TicketRepository


@dataclass
class AddCommentInput:
    """Input DTO for adding a comment."""

    ticket_id: str
    author_id: str
    body: str


class AddCommentUseCase:
    """Adds a comment after validating the ticket exists and is not closed."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        comment_repo: CommentRepository,
    ):
        self._ticket_repo = ticket_repo
        self._comment_repo = comment_repo

    def execute(self, input_data: AddCommentInput) -> Comment:
        # ── Validate ticket exists ──
        ticket = self._ticket_repo.get_by_id(input_data.ticket_id)
        if ticket is None:
            raise TicketNotFoundError(input_data.ticket_id)

        if ticket.status == TicketStatus.CLOSED:
            raise TicketAlreadyClosedError(input_data.ticket_id)

        # ── Validate body ──
        if not input_data.body or len(input_data.body.strip()) < 1:
            raise InvalidTicketDataError("Comment body cannot be empty")

        # ── Create and persist ──
        comment = Comment(
            ticket_id=input_data.ticket_id,
            author_id=input_data.author_id,
            body=input_data.body.strip(),
        )

        return self._comment_repo.save(comment)
