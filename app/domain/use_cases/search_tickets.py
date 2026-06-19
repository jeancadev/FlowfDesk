"""
Use Case: Search Tickets

Full-text search with optional filters, powered by Elasticsearch.
Falls back to database listing if search is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.ports.repositories import SearchPort, TicketRepository


@dataclass
class SearchTicketsInput:
    """Input DTO for searching tickets."""

    query: str
    status: str | None = None
    priority: str | None = None
    assignee_id: str | None = None
    limit: int = 20


class SearchTicketsUseCase:
    """Searches tickets using full-text search or falls back to DB listing."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        search: SearchPort,
    ):
        self._repo = ticket_repo
        self._search = search

    def execute(self, input_data: SearchTicketsInput) -> list[dict[str, Any]]:
        filters: dict[str, Any] = {}
        if input_data.status:
            filters["status"] = input_data.status
        if input_data.priority:
            filters["priority"] = input_data.priority
        if input_data.assignee_id:
            filters["assignee_id"] = input_data.assignee_id

        try:
            results = self._search.search_tickets(
                query=input_data.query,
                filters=filters if filters else None,
                limit=input_data.limit,
            )
            return results
        except Exception:
            # Fallback: return tickets from DB (no full-text, just filtered list)
            tickets = self._repo.list_all(
                status=input_data.status,
                assignee_id=input_data.assignee_id,
                limit=input_data.limit,
            )
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "status": t.status.value
                    if hasattr(t.status, "value")
                    else t.status,
                    "priority": t.priority.value
                    if hasattr(t.priority, "value")
                    else t.priority,
                    "creator_id": t.creator_id,
                    "created_at": t.created_at.isoformat(),
                }
                for t in tickets
            ]
