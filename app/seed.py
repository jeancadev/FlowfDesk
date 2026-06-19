"""
FlowDesk Seed Script — Populate database with sample data.

Run after migrations to have realistic demo data:
    python -m app.seed

Creates sample users, tickets, and comments for development and testing.
"""

from app.core.logging import get_logger, setup_logging
from app.domain.entities.ticket import (
    Comment,
    Ticket,
    TicketPriority,
    User,
    UserRole,
)
from app.infrastructure.database.repositories.postgres_repos import (
    PostgresCommentRepository,
    PostgresTicketRepository,
    PostgresUserRepository,
)
from app.infrastructure.database.session import get_session

logger = get_logger(__name__)


SAMPLE_USERS = [
    User(
        id="user-001",
        email="admin@flowdesk.io",
        full_name="María García",
        role=UserRole.ADMIN,
    ),
    User(
        id="user-002",
        email="agent1@flowdesk.io",
        full_name="Carlos Ramírez",
        role=UserRole.AGENT,
    ),
    User(
        id="user-003",
        email="agent2@flowdesk.io",
        full_name="Ana López",
        role=UserRole.AGENT,
    ),
    User(
        id="user-004",
        email="customer1@company.com",
        full_name="Juan Rodríguez",
        role=UserRole.CUSTOMER,
    ),
    User(
        id="user-005",
        email="customer2@company.com",
        full_name="Laura Martínez",
        role=UserRole.CUSTOMER,
    ),
]


SAMPLE_TICKETS = [
    Ticket.create(
        title="Login page returns 500 error after deployment",
        description=(
            "After the latest deployment (v2.3.1), users are seeing a 500 "
            "Internal Server Error when trying to log in. This affects all "
            "users and is critical since nobody can access the system. The "
            "error seems to originate from the auth middleware."
        ),
        creator_id="user-004",
        priority=TicketPriority.CRITICAL,
        tags=["bug", "auth", "production", "deployment"],
        assignee_id="user-002",
    ),
    Ticket.create(
        title="Dashboard charts not loading for large datasets",
        description=(
            "When a user has more than 1000 records, the dashboard charts "
            "fail to render. The browser console shows a JavaScript heap out "
            "of memory error. Need to implement pagination or lazy loading "
            "for chart data."
        ),
        creator_id="user-005",
        priority=TicketPriority.HIGH,
        tags=["bug", "performance", "dashboard"],
        assignee_id="user-003",
    ),
    Ticket.create(
        title="Feature request: Export tickets to CSV",
        description=(
            "Multiple customers have requested the ability to export their "
            "ticket history to CSV format for reporting purposes. This should "
            "include all ticket fields plus comments count."
        ),
        creator_id="user-004",
        priority=TicketPriority.MEDIUM,
        tags=["feature", "export", "reporting"],
    ),
    Ticket.create(
        title="Email notifications arriving with delay",
        description=(
            "Email notifications for ticket updates are arriving 15-30 "
            "minutes late. The Kafka consumer lag metrics show increasing "
            "delay. Need to investigate consumer group rebalancing."
        ),
        creator_id="user-005",
        priority=TicketPriority.HIGH,
        tags=["bug", "notifications", "kafka"],
        assignee_id="user-002",
    ),
    Ticket.create(
        title="Add dark mode support to settings page",
        description=(
            "Users have been asking for dark mode. We should add a toggle in "
            "user settings that persists the preference. Consider using CSS "
            "custom properties for theme switching."
        ),
        creator_id="user-004",
        priority=TicketPriority.LOW,
        tags=["feature", "ui", "accessibility"],
    ),
]


def seed_database() -> None:
    """Insert sample data into the database."""
    setup_logging("INFO")
    session = get_session()

    try:
        user_repo = PostgresUserRepository(session)
        ticket_repo = PostgresTicketRepository(session)
        comment_repo = PostgresCommentRepository(session)

        # Seed users
        for user in SAMPLE_USERS:
            existing = user_repo.get_by_email(user.email)
            if not existing:
                user_repo.save(user)
                logger.info("user_seeded", email=user.email, role=user.role.value)

        # Seed tickets
        for ticket in SAMPLE_TICKETS:
            ticket_repo.save(ticket)
            logger.info("ticket_seeded", title=ticket.title[:50])

        # Seed some comments
        tickets = ticket_repo.list_all(limit=5)
        if tickets:
            sample_comments = [
                Comment(
                    ticket_id=tickets[0].id,
                    author_id="user-002",
                    body="Investigating now. Checking the auth middleware logs.",
                ),
                Comment(
                    ticket_id=tickets[0].id,
                    author_id="user-002",
                    body=(
                        "Found the issue — the JWT secret was rotated during "
                        "deployment but the env var wasn't updated. Deploying "
                        "fix now."
                    ),
                ),
                Comment(
                    ticket_id=tickets[1].id,
                    author_id="user-003",
                    body=(
                        "Reproduced the issue. Working on implementing "
                        "virtual scrolling for the chart data."
                    ),
                ),
            ]
            for comment in sample_comments:
                comment_repo.save(comment)
                logger.info("comment_seeded", ticket_id=comment.ticket_id[:8])

        logger.info(
            "seed_completed", users=len(SAMPLE_USERS), tickets=len(SAMPLE_TICKETS)
        )

    except Exception as e:
        logger.error("seed_failed", error=str(e))
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
