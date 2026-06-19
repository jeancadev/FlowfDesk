"""
FlowDesk Dependency Injection Container.

Wires together infrastructure implementations with domain ports.
No DI framework needed — simple, explicit Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class Container:
    """
    Dependency Injection container.

    Lazy-initializes adapters and provides them as properties.
    Each request gets a fresh DB session; other adapters are shared.

    All infrastructure imports are deferred (lazy) so that importing
    this module never triggers connections to external services.
    This is critical for tests to run without Docker.
    """

    def __init__(self) -> None:
        self._cache: Any = None
        self._search: Any = None
        self._broker: Any = None
        self._storage: Any = None

    # ── DB Session (per-request) ──

    def get_db_session(self) -> Session:
        """Create a new database session for each request."""
        from app.infrastructure.database.session import get_session

        return get_session()

    # ── Repositories (require a session) ──

    def ticket_repository(self, session: Session):
        from app.infrastructure.database.repositories.postgres_repos import (
            PostgresTicketRepository,
        )

        return PostgresTicketRepository(session)

    def user_repository(self, session: Session):
        from app.infrastructure.database.repositories.postgres_repos import (
            PostgresUserRepository,
        )

        return PostgresUserRepository(session)

    def comment_repository(self, session: Session):
        from app.infrastructure.database.repositories.postgres_repos import (
            PostgresCommentRepository,
        )

        return PostgresCommentRepository(session)

    def attachment_repository(self, session: Session):
        from app.infrastructure.database.repositories.postgres_repos import (
            PostgresAttachmentRepository,
        )

        return PostgresAttachmentRepository(session)

    # ── Shared Adapters (lazy singletons) ──

    @property
    def cache(self):
        if self._cache is None:
            from app.infrastructure.cache.redis_cache import RedisCache

            self._cache = RedisCache()
        return self._cache

    @property
    def search(self):
        if self._search is None:
            from app.infrastructure.search.elasticsearch_adapter import (
                ElasticsearchAdapter,
            )

            self._search = ElasticsearchAdapter()
        return self._search

    @property
    def broker(self):
        if self._broker is None:
            from app.infrastructure.messaging.kafka_producer import (
                KafkaMessageBroker,
            )

            self._broker = KafkaMessageBroker()
        return self._broker

    @property
    def storage(self):
        if self._storage is None:
            from app.infrastructure.storage.s3_adapter import S3StorageAdapter

            self._storage = S3StorageAdapter()
        return self._storage


# Module-level singleton
container = Container()
