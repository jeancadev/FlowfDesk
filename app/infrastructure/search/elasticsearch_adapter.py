"""
Elasticsearch Search Adapter — Implementation of SearchPort.

Provides full-text search for tickets by content, tags, and user.
Handles index creation, document indexing, and multi-field search queries.
"""

from __future__ import annotations

from typing import Any

from elasticsearch import Elasticsearch, NotFoundError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.entities.ticket import Ticket

logger = get_logger(__name__)

TICKET_INDEX = "flowdesk_tickets"

# Elasticsearch mapping with proper analyzers for full-text search
TICKET_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "standard",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "description": {"type": "text", "analyzer": "standard"},
            "status": {"type": "keyword"},
            "priority": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "creator_id": {"type": "keyword"},
            "assignee_id": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
            "closed_at": {"type": "date"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
}


class ElasticsearchAdapter:
    """Elasticsearch implementation of the SearchPort interface."""

    def __init__(self, url: str | None = None):
        settings = get_settings()
        self._client = Elasticsearch(
            url or settings.ELASTICSEARCH_URL,
            request_timeout=10,
        )
        self._ensure_index()

    def _ensure_index(self) -> None:
        """Create the ticket index if it doesn't exist."""
        try:
            if not self._client.indices.exists(index=TICKET_INDEX):
                self._client.indices.create(index=TICKET_INDEX, body=TICKET_MAPPING)
                logger.info("elasticsearch_index_created", index=TICKET_INDEX)
        except Exception as e:
            logger.warning("elasticsearch_index_creation_failed", error=str(e))

    def index_ticket(self, ticket: Ticket) -> None:
        """Index or update a ticket document."""
        doc = {
            "id": ticket.id,
            "title": ticket.title,
            "description": ticket.description,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "tags": ticket.tags,
            "creator_id": ticket.creator_id,
            "assignee_id": ticket.assignee_id,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        }
        self._client.index(index=TICKET_INDEX, id=ticket.id, document=doc)
        logger.info("ticket_indexed", ticket_id=ticket.id)

    def search_tickets(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Full-text search across title, description, and tags."""
        must_clauses: list[dict[str, Any]] = []
        filter_clauses: list[dict[str, Any]] = []

        # Multi-match query across searchable fields
        if query:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "description^2", "tags^1.5"],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                }
            )

        # Apply keyword filters
        if filters:
            for field, value in filters.items():
                filter_clauses.append({"term": {field: value}})

        body: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": must_clauses or [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}},
                {"created_at": {"order": "desc"}},
            ],
        }

        response = self._client.search(index=TICKET_INDEX, body=body)
        hits = response.get("hits", {}).get("hits", [])

        return [{**hit["_source"], "_score": hit["_score"]} for hit in hits]

    def delete_ticket(self, ticket_id: str) -> None:
        """Remove a ticket from the search index."""
        try:
            self._client.delete(index=TICKET_INDEX, id=ticket_id)
        except NotFoundError:
            pass
