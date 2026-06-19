"""
Test Configuration and Fixtures.

Provides shared fixtures for unit and integration tests.
Unit tests use mocks; integration tests use real services via Docker.
"""

import pytest

from app.domain.entities.ticket import (
    Ticket,
    TicketPriority,
    User,
    UserRole,
)

# ─── Mock Implementations ───────────────────────────────────────────


class MockTicketRepository:
    """In-memory mock for TicketRepository port."""

    def __init__(self):
        self._tickets: dict[str, Ticket] = {}

    def save(self, ticket: Ticket) -> Ticket:
        self._tickets[ticket.id] = ticket
        return ticket

    def get_by_id(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)

    def list_all(self, status=None, assignee_id=None, limit=50, offset=0):
        tickets = list(self._tickets.values())
        if status:
            tickets = [t for t in tickets if t.status.value == status]
        if assignee_id:
            tickets = [t for t in tickets if t.assignee_id == assignee_id]
        return tickets[offset : offset + limit]

    def update(self, ticket: Ticket) -> Ticket:
        self._tickets[ticket.id] = ticket
        return ticket

    def delete(self, ticket_id: str) -> bool:
        if ticket_id in self._tickets:
            del self._tickets[ticket_id]
            return True
        return False

    def count(self, status=None, assignee_id=None):
        return len(self.list_all(status=status, assignee_id=assignee_id))


class MockCommentRepository:
    """In-memory mock for CommentRepository port."""

    def __init__(self):
        self._comments = []

    def save(self, comment):
        self._comments.append(comment)
        return comment

    def get_by_ticket_id(self, ticket_id):
        return [c for c in self._comments if c.ticket_id == ticket_id]


class MockUserRepository:
    """In-memory mock for UserRepository port."""

    def __init__(self):
        self._users: dict[str, User] = {}

    def save(self, user: User) -> User:
        self._users[user.id] = user
        return user

    def get_by_id(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def list_all(self, limit: int = 50, offset: int = 0) -> list[User]:
        users = list(self._users.values())
        return users[offset : offset + limit]


class MockSearchPort:
    """Mock for SearchPort — stores indexed documents in memory."""

    def __init__(self):
        self._indexed: dict[str, dict] = {}

    def index_ticket(self, ticket):
        self._indexed[ticket.id] = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "creator_id": ticket.creator_id,
            "created_at": ticket.created_at.isoformat(),
        }

    def search_tickets(self, query, filters=None, limit=20):
        results = []
        for doc in self._indexed.values():
            if (
                query.lower() in doc["title"].lower()
                or query.lower() in doc["description"].lower()
            ):
                results.append({**doc, "_score": 1.0})
        return results[:limit]

    def delete_ticket(self, ticket_id):
        self._indexed.pop(ticket_id, None)


class MockMessageBroker:
    """Mock for MessageBroker — records published messages."""

    def __init__(self):
        self.published: list[tuple[str, dict]] = []

    def publish(self, topic, message):
        self.published.append((topic, message))

    def close(self):
        pass


class MockCachePort:
    """Mock for CachePort — in-memory cache."""

    def __init__(self):
        self._store: dict[str, str] = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, ttl_seconds=300):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)

    def increment(self, key, ttl_seconds=60):
        current = int(self._store.get(key, "0"))
        current += 1
        self._store[key] = str(current)
        return current


class MockStoragePort:
    """Mock for StoragePort — in-memory file storage."""

    def __init__(self):
        self._files: dict[str, bytes] = {}

    def upload(self, file_data, key, content_type="application/octet-stream"):
        self._files[key] = file_data
        return key

    def get_presigned_url(self, key, expiration=3600):
        return f"https://mock-s3.local/{key}?expires={expiration}"

    def delete(self, key):
        self._files.pop(key, None)


class MockAttachmentRepository:
    """In-memory mock for AttachmentRepository port."""

    def __init__(self):
        self._attachments = []

    def save(self, attachment):
        self._attachments.append(attachment)
        return attachment

    def get_by_ticket_id(self, ticket_id):
        return [a for a in self._attachments if a.ticket_id == ticket_id]


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_ticket_repo():
    return MockTicketRepository()


@pytest.fixture
def mock_comment_repo():
    return MockCommentRepository()


@pytest.fixture
def mock_search():
    return MockSearchPort()


@pytest.fixture
def mock_broker():
    return MockMessageBroker()


@pytest.fixture
def mock_cache():
    return MockCachePort()


@pytest.fixture
def mock_storage():
    return MockStoragePort()


@pytest.fixture
def mock_attachment_repo():
    return MockAttachmentRepository()


@pytest.fixture
def sample_user():
    return User(
        id="user-001",
        email="agent@flowdesk.io",
        full_name="Test Agent",
        role=UserRole.AGENT,
    )


@pytest.fixture
def sample_ticket():
    return Ticket.create(
        title="Login page returns 500 error",
        description=(
            "When clicking the login button with valid credentials, "
            "the server returns a 500 error."
        ),
        creator_id="user-001",
        priority=TicketPriority.HIGH,
        tags=["bug", "auth", "production"],
    )


@pytest.fixture
def flask_app():
    """Create a Flask test app with fully mocked infrastructure.

    Mocks all infrastructure connections (Redis, ES, Kafka, S3)
    AND the database session/repository layer so tests run without
    any external services.
    """
    from unittest.mock import MagicMock

    from app.core.container import container
    from app.main import create_app

    # Shared in-memory mock repos for the lifetime of a test
    _ticket_repo = MockTicketRepository()
    _user_repo = MockUserRepository()
    _comment_repo = MockCommentRepository()
    _attachment_repo = MockAttachmentRepository()

    _mock_search = MockSearchPort()
    _mock_broker = MockMessageBroker()
    _mock_cache = MockCachePort()
    _mock_cache.ping = lambda: True
    _mock_storage = MockStoragePort()

    # Patch the container singleton methods
    original_get_db_session = container.get_db_session
    original_ticket_repo = container.ticket_repository
    original_user_repo = container.user_repository
    original_comment_repo = container.comment_repository
    original_attachment_repo = container.attachment_repository

    mock_session = MagicMock()
    mock_session.close = MagicMock()

    container.get_db_session = lambda: mock_session
    container.ticket_repository = lambda session: _ticket_repo
    container.user_repository = lambda session: _user_repo
    container.comment_repository = lambda session: _comment_repo
    container.attachment_repository = lambda session: _attachment_repo
    container._cache = _mock_cache
    container._search = _mock_search
    container._broker = _mock_broker
    container._storage = _mock_storage

    app = create_app(testing=True)

    yield app

    # Restore originals
    container.get_db_session = original_get_db_session
    container.ticket_repository = original_ticket_repo
    container.user_repository = original_user_repo
    container.comment_repository = original_comment_repo
    container.attachment_repository = original_attachment_repo
    container._cache = None
    container._search = None
    container._broker = None
    container._storage = None


@pytest.fixture
def client(flask_app):
    """Flask test client for API integration tests."""
    return flask_app.test_client()
