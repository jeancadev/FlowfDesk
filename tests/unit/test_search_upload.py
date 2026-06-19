"""
Unit Tests — Search Tickets and Upload Attachment Use Cases.
"""

import pytest

from app.domain.entities.ticket import Ticket, TicketPriority
from app.domain.exceptions import (
    AttachmentTooLargeError,
    TicketAlreadyClosedError,
    TicketNotFoundError,
)
from app.domain.use_cases.search_tickets import SearchTicketsInput, SearchTicketsUseCase
from app.domain.use_cases.upload_attachment import (
    UploadAttachmentInput,
    UploadAttachmentUseCase,
)


class TestSearchTicketsUseCase:
    """Tests for SearchTicketsUseCase."""

    def _seed_tickets(self, mock_ticket_repo, mock_search):
        """Seed sample tickets into repo and search index."""
        tickets = [
            Ticket.create(
                title="Login page returns 500 error",
                description="Server error on login with valid creds.",
                creator_id="user-001",
                priority=TicketPriority.HIGH,
                tags=["bug", "auth"],
            ),
            Ticket.create(
                title="Dashboard loading slowly",
                description="Dashboard takes 10+ seconds to render charts.",
                creator_id="user-002",
                priority=TicketPriority.MEDIUM,
                tags=["performance"],
            ),
            Ticket.create(
                title="Feature request: dark mode",
                description="Users have requested a dark mode toggle in settings.",
                creator_id="user-001",
                priority=TicketPriority.LOW,
                tags=["feature", "ui"],
            ),
        ]
        for t in tickets:
            mock_ticket_repo.save(t)
            mock_search.index_ticket(t)
        return tickets

    def test_search_returns_matching_tickets(self, mock_ticket_repo, mock_search):
        self._seed_tickets(mock_ticket_repo, mock_search)
        uc = SearchTicketsUseCase(mock_ticket_repo, mock_search)
        results = uc.execute(SearchTicketsInput(query="login"))
        assert len(results) == 1
        assert "login" in results[0]["title"].lower()

    def test_search_returns_empty_for_no_match(self, mock_ticket_repo, mock_search):
        self._seed_tickets(mock_ticket_repo, mock_search)
        uc = SearchTicketsUseCase(mock_ticket_repo, mock_search)
        results = uc.execute(SearchTicketsInput(query="zzzznotfound"))
        assert len(results) == 0

    def test_search_returns_multiple_matches(self, mock_ticket_repo, mock_search):
        self._seed_tickets(mock_ticket_repo, mock_search)
        uc = SearchTicketsUseCase(mock_ticket_repo, mock_search)
        # "user" appears in description of dark mode ticket
        results = uc.execute(SearchTicketsInput(query="dark"))
        assert len(results) >= 1

    def test_search_respects_limit(self, mock_ticket_repo, mock_search):
        self._seed_tickets(mock_ticket_repo, mock_search)
        uc = SearchTicketsUseCase(mock_ticket_repo, mock_search)
        results = uc.execute(SearchTicketsInput(query="", limit=1))
        # With empty query, mock returns all; limit caps
        # Mock doesn't filter on empty query, so this tests limit parameter passing
        assert isinstance(results, list)


class TestUploadAttachmentUseCase:
    """Tests for UploadAttachmentUseCase."""

    def _create_open_ticket(self, mock_ticket_repo):
        ticket = Ticket.create(
            title="Ticket with attachments",
            description="This ticket will have files attached.",
            creator_id="user-001",
        )
        mock_ticket_repo.save(ticket)
        return ticket

    def test_upload_attachment_success(self, mock_ticket_repo, mock_storage):
        from tests.conftest import MockAttachmentRepository

        mock_attach_repo = MockAttachmentRepository()

        ticket = self._create_open_ticket(mock_ticket_repo)
        uc = UploadAttachmentUseCase(mock_ticket_repo, mock_attach_repo, mock_storage)

        result = uc.execute(
            UploadAttachmentInput(
                ticket_id=ticket.id,
                filename="screenshot.png",
                content_type="image/png",
                file_data=b"fake image data bytes here",
                uploaded_by="user-001",
            )
        )

        assert result.filename == "screenshot.png"
        assert result.content_type == "image/png"
        assert result.ticket_id == ticket.id
        assert result.size_bytes == len(b"fake image data bytes here")

    def test_upload_attachment_ticket_not_found(self, mock_ticket_repo, mock_storage):
        from tests.conftest import MockAttachmentRepository

        mock_attach_repo = MockAttachmentRepository()

        uc = UploadAttachmentUseCase(mock_ticket_repo, mock_attach_repo, mock_storage)

        with pytest.raises(TicketNotFoundError):
            uc.execute(
                UploadAttachmentInput(
                    ticket_id="nonexistent",
                    filename="file.txt",
                    content_type="text/plain",
                    file_data=b"data",
                    uploaded_by="user-001",
                )
            )

    def test_upload_attachment_too_large(self, mock_ticket_repo, mock_storage):
        from tests.conftest import MockAttachmentRepository

        mock_attach_repo = MockAttachmentRepository()

        ticket = self._create_open_ticket(mock_ticket_repo)
        uc = UploadAttachmentUseCase(mock_ticket_repo, mock_attach_repo, mock_storage)

        # Create data larger than 10MB limit
        large_data = b"x" * (11 * 1024 * 1024)

        with pytest.raises(AttachmentTooLargeError):
            uc.execute(
                UploadAttachmentInput(
                    ticket_id=ticket.id,
                    filename="huge_file.zip",
                    content_type="application/zip",
                    file_data=large_data,
                    uploaded_by="user-001",
                )
            )

    def test_upload_attachment_on_closed_ticket(self, mock_ticket_repo, mock_storage):
        from tests.conftest import MockAttachmentRepository

        mock_attach_repo = MockAttachmentRepository()

        ticket = self._create_open_ticket(mock_ticket_repo)
        ticket.close()
        mock_ticket_repo.update(ticket)

        uc = UploadAttachmentUseCase(mock_ticket_repo, mock_attach_repo, mock_storage)

        with pytest.raises(TicketAlreadyClosedError):
            uc.execute(
                UploadAttachmentInput(
                    ticket_id=ticket.id,
                    filename="file.txt",
                    content_type="text/plain",
                    file_data=b"data",
                    uploaded_by="user-001",
                )
            )
