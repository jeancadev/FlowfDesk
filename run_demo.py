"""
FlowDesk Demo Server — Runs the API with in-memory mocks.

No external services required (no Docker, no PostgreSQL, no Redis, etc.).
All data lives in memory for the duration of the session.

Usage:
    python run_demo.py
    Then open: http://localhost:8000/swagger/
"""

from unittest.mock import MagicMock

from app.domain.entities.ticket import (
    Ticket,
    TicketPriority,
    User,
    UserRole,
)

# ─── In-Memory Mock Implementations ─────────────────────────────────


class MockTicketRepository:
    def __init__(self):
        self._tickets: dict[str, Ticket] = {}

    def save(self, ticket):
        self._tickets[ticket.id] = ticket
        return ticket

    def get_by_id(self, ticket_id):
        return self._tickets.get(ticket_id)

    def list_all(self, status=None, assignee_id=None, limit=50, offset=0):
        tickets = list(self._tickets.values())
        if status:
            tickets = [t for t in tickets if t.status.value == status]
        if assignee_id:
            tickets = [t for t in tickets if t.assignee_id == assignee_id]
        return tickets[offset : offset + limit]

    def update(self, ticket):
        self._tickets[ticket.id] = ticket
        return ticket

    def delete(self, ticket_id):
        if ticket_id in self._tickets:
            del self._tickets[ticket_id]
            return True
        return False

    def count(self, status=None, assignee_id=None):
        return len(self.list_all(status=status, assignee_id=assignee_id))


class MockUserRepository:
    def __init__(self):
        self._users: dict[str, User] = {}

    def save(self, user):
        self._users[user.id] = user
        return user

    def get_by_id(self, user_id):
        return self._users.get(user_id)

    def get_by_email(self, email):
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def list_all(self, limit=50, offset=0):
        users = list(self._users.values())
        return users[offset : offset + limit]


class MockCommentRepository:
    def __init__(self):
        self._comments = []

    def save(self, comment):
        self._comments.append(comment)
        return comment

    def get_by_ticket_id(self, ticket_id):
        return [c for c in self._comments if c.ticket_id == ticket_id]


class MockAttachmentRepository:
    def __init__(self):
        self._attachments = []

    def save(self, attachment):
        self._attachments.append(attachment)
        return attachment

    def get_by_ticket_id(self, ticket_id):
        return [a for a in self._attachments if a.ticket_id == ticket_id]


class MockSearchPort:
    def __init__(self):
        self._indexed = {}

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
    def __init__(self):
        self.published = []

    def publish(self, topic, message):
        self.published.append((topic, message))
        print(f"  [EVENT] {topic} -> {message.get('ticket_id', 'N/A')}")

    def close(self):
        pass


class MockCachePort:
    def __init__(self):
        self._store = {}

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

    def ping(self):
        return True


class MockStoragePort:
    def __init__(self):
        self._files = {}

    def upload(self, file_data, key, content_type="application/octet-stream"):
        self._files[key] = file_data
        return key

    def get_presigned_url(self, key, expiration=3600):
        return f"https://mock-s3.local/{key}?expires={expiration}"

    def delete(self, key):
        self._files.pop(key, None)


# ─── Setup & Run ─────────────────────────────────────────────────────


def main():
    from app.core.container import container

    # Create shared mock instances
    ticket_repo = MockTicketRepository()
    user_repo = MockUserRepository()
    comment_repo = MockCommentRepository()
    attachment_repo = MockAttachmentRepository()
    search = MockSearchPort()
    broker = MockMessageBroker()
    cache = MockCachePort()
    storage = MockStoragePort()

    # Patch the container
    mock_session = MagicMock()
    mock_session.close = MagicMock()

    container.get_db_session = lambda: mock_session
    container.ticket_repository = lambda session: ticket_repo
    container.user_repository = lambda session: user_repo
    container.comment_repository = lambda session: comment_repo
    container.attachment_repository = lambda session: attachment_repo
    container._cache = cache
    container._search = search
    container._broker = broker
    container._storage = storage

    # Seed some demo data
    print("\n[*] Seeding demo data...")

    demo_user = User(
        id="user-001",
        email="agent@flowdesk.io",
        full_name="Maria Garcia",
        role=UserRole.AGENT,
    )
    user_repo.save(demo_user)

    admin_user = User(
        id="user-002",
        email="admin@flowdesk.io",
        full_name="Carlos Mendez",
        role=UserRole.ADMIN,
    )
    user_repo.save(admin_user)

    demo_tickets = [
        Ticket.create(
            title="Login page returns 500 error",
            description="When clicking the login button with valid credentials, the server returns a 500 error. This started after the last deployment.",
            creator_id="user-001",
            priority=TicketPriority.HIGH,
            tags=["bug", "auth", "production"],
        ),
        Ticket.create(
            title="Dashboard loading slowly",
            description="Dashboard takes 10+ seconds to render charts. Performance issue affecting multiple users.",
            creator_id="user-002",
            priority=TicketPriority.MEDIUM,
            tags=["performance", "dashboard"],
        ),
        Ticket.create(
            title="Feature request: dark mode",
            description="Users have requested a dark mode toggle in settings. Multiple customer complaints about eye strain.",
            creator_id="user-001",
            priority=TicketPriority.LOW,
            tags=["feature", "ui"],
        ),
    ]

    for t in demo_tickets:
        ticket_repo.save(t)
        search.index_ticket(t)

    print(f"  [OK] Created {len([demo_user, admin_user])} users")
    print(f"  [OK] Created {len(demo_tickets)} tickets")
    print(f"  [OK] Indexed {len(demo_tickets)} tickets for search")

    # Create the Flask app
    from app.main import create_app

    app = create_app(testing=False)

    print("\n" + "=" * 60)
    print("  FlowDesk API -- Demo Mode (in-memory)")
    print("=" * 60)
    print("  Swagger UI:  http://localhost:8000/swagger/")
    print("  Health:      http://localhost:8000/health")
    print("  Tickets:     http://localhost:8000/api/v1/tickets/")
    print("  Users:       http://localhost:8000/api/v1/users/")
    print("  Search:      http://localhost:8000/api/v1/tickets/search?q=login")
    print("=" * 60)
    print("  Press Ctrl+C to stop\n")

    app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
