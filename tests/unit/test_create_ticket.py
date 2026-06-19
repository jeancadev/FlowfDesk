"""
Unit Tests — Create Ticket Use Case.

Tests the business logic in isolation, with all infrastructure mocked.
Naming convention: test_[unit]_[condition]_[expected_behavior]
"""

import pytest

from app.domain.entities.ticket import TicketPriority, TicketStatus
from app.domain.exceptions import InvalidTicketDataError
from app.domain.use_cases.create_ticket import CreateTicketInput, CreateTicketUseCase


class TestCreateTicketUseCase:
    """Tests for CreateTicketUseCase business logic."""

    def test_create_ticket_success_with_valid_data(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        """Happy path: valid input creates a ticket with correct defaults."""
        use_case = CreateTicketUseCase(
            ticket_repo=mock_ticket_repo,
            search=mock_search,
            broker=mock_broker,
        )
        input_data = CreateTicketInput(
            title="Login page returns 500 error",
            description=(
                "When clicking the login button with valid credentials, "
                "the server returns a 500 error."
            ),
            creator_id="user-001",
            priority="high",
            tags=["bug", "auth"],
        )

        ticket = use_case.execute(input_data)

        assert ticket.id is not None
        assert ticket.title == "Login page returns 500 error"
        assert ticket.status == TicketStatus.OPEN
        assert ticket.priority == TicketPriority.HIGH
        assert ticket.tags == ["bug", "auth"]
        assert ticket.creator_id == "user-001"

    def test_create_ticket_publishes_event(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        """Ticket creation should publish a ticket.created event."""
        use_case = CreateTicketUseCase(
            ticket_repo=mock_ticket_repo,
            search=mock_search,
            broker=mock_broker,
        )
        input_data = CreateTicketInput(
            title="Test event publishing",
            description="This ticket should trigger a Kafka event on creation.",
            creator_id="user-001",
        )

        use_case.execute(input_data)

        assert len(mock_broker.published) == 1
        topic, message = mock_broker.published[0]
        assert topic == "ticket.created"
        assert message["title"] == "Test event publishing"

    def test_create_ticket_indexes_for_search(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        """Ticket should be indexed in Elasticsearch on creation."""
        use_case = CreateTicketUseCase(
            ticket_repo=mock_ticket_repo,
            search=mock_search,
            broker=mock_broker,
        )
        input_data = CreateTicketInput(
            title="Searchable ticket",
            description="This ticket should appear in search results after creation.",
            creator_id="user-001",
        )

        ticket = use_case.execute(input_data)

        # Verify it was indexed
        results = mock_search.search_tickets("Searchable")
        assert len(results) == 1
        assert results[0]["id"] == ticket.id

    def test_create_ticket_fails_with_short_title(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        """Title shorter than 3 characters should raise InvalidTicketDataError."""
        use_case = CreateTicketUseCase(
            ticket_repo=mock_ticket_repo,
            search=mock_search,
            broker=mock_broker,
        )
        input_data = CreateTicketInput(
            title="AB",
            description="Valid description for the ticket.",
            creator_id="user-001",
        )

        with pytest.raises(InvalidTicketDataError) as exc_info:
            use_case.execute(input_data)

        assert "Title must be at least 3 characters" in str(exc_info.value)

    def test_create_ticket_fails_with_short_description(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        """Short descriptions should raise InvalidTicketDataError."""
        use_case = CreateTicketUseCase(
            ticket_repo=mock_ticket_repo,
            search=mock_search,
            broker=mock_broker,
        )
        input_data = CreateTicketInput(
            title="Valid title",
            description="Short",
            creator_id="user-001",
        )

        with pytest.raises(InvalidTicketDataError):
            use_case.execute(input_data)

    def test_create_ticket_fails_with_invalid_priority(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        """Invalid priority value should raise InvalidTicketDataError."""
        use_case = CreateTicketUseCase(
            ticket_repo=mock_ticket_repo,
            search=mock_search,
            broker=mock_broker,
        )
        input_data = CreateTicketInput(
            title="Valid title here",
            description="Valid description for the ticket here.",
            creator_id="user-001",
            priority="urgent",  # Not a valid priority
        )

        with pytest.raises(InvalidTicketDataError) as exc_info:
            use_case.execute(input_data)

        assert "Invalid priority" in str(exc_info.value)

    def test_create_ticket_default_priority_is_medium(
        self, mock_ticket_repo, mock_search, mock_broker
    ):
        """Default priority should be medium when not specified."""
        use_case = CreateTicketUseCase(
            ticket_repo=mock_ticket_repo,
            search=mock_search,
            broker=mock_broker,
        )
        input_data = CreateTicketInput(
            title="Default priority ticket",
            description="This ticket should have medium priority by default.",
            creator_id="user-001",
        )

        ticket = use_case.execute(input_data)

        assert ticket.priority == TicketPriority.MEDIUM
