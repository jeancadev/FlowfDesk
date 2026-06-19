"""
Ticket Routes — Flask-RESTX namespace for ticket CRUD + search.

Thin endpoints: validate input, delegate to use cases, format output.
No business logic here.
"""

from flask import request
from flask_restx import Namespace, Resource

from app.api.v1.schemas.ticket_schemas import register_ticket_schemas
from app.core.container import container
from app.domain.use_cases.add_comment import AddCommentInput, AddCommentUseCase
from app.domain.use_cases.close_ticket import CloseTicketUseCase
from app.domain.use_cases.create_ticket import CreateTicketInput, CreateTicketUseCase
from app.domain.use_cases.search_tickets import SearchTicketsInput, SearchTicketsUseCase
from app.domain.use_cases.update_ticket import UpdateTicketInput, UpdateTicketUseCase

# Create namespace
tickets_ns = Namespace(
    "tickets",
    description="Ticket management operations",
    path="/api/v1/tickets",
)

# Register schemas
schemas = register_ticket_schemas(tickets_ns)


def _ticket_to_dict(ticket):
    """Serialize a Ticket entity to dict for API response."""
    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status.value
        if hasattr(ticket.status, "value")
        else ticket.status,
        "priority": ticket.priority.value
        if hasattr(ticket.priority, "value")
        else ticket.priority,
        "tags": ticket.tags,
        "creator_id": ticket.creator_id,
        "assignee_id": ticket.assignee_id,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
    }


def _comment_to_dict(comment):
    """Serialize a Comment entity to dict."""
    return {
        "id": comment.id,
        "ticket_id": comment.ticket_id,
        "author_id": comment.author_id,
        "body": comment.body,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@tickets_ns.route("/")
class TicketList(Resource):
    """Ticket collection endpoints."""

    @tickets_ns.doc("list_tickets")
    @tickets_ns.marshal_list_with(schemas["ticket_response"])
    @tickets_ns.param("status", "Filter by status", type="string")
    @tickets_ns.param("assignee_id", "Filter by assignee", type="string")
    @tickets_ns.param("limit", "Max results (default: 50)", type="integer")
    @tickets_ns.param("offset", "Pagination offset (default: 0)", type="integer")
    def get(self):
        """List all tickets with optional filters."""
        session = container.get_db_session()
        try:
            repo = container.ticket_repository(session)
            tickets = repo.list_all(
                status=request.args.get("status"),
                assignee_id=request.args.get("assignee_id"),
                limit=int(request.args.get("limit", 50)),
                offset=int(request.args.get("offset", 0)),
            )
            return [_ticket_to_dict(t) for t in tickets]
        finally:
            session.close()

    @tickets_ns.doc("create_ticket")
    @tickets_ns.expect(schemas["create_ticket"], validate=True)
    @tickets_ns.marshal_with(schemas["ticket_response"], code=201)
    @tickets_ns.response(400, "Validation error")
    def post(self):
        """Create a new ticket."""
        data = request.json
        session = container.get_db_session()
        try:
            use_case = CreateTicketUseCase(
                ticket_repo=container.ticket_repository(session),
                search=container.search,
                broker=container.broker,
            )
            input_data = CreateTicketInput(
                title=data["title"],
                description=data["description"],
                creator_id=data["creator_id"],
                priority=data.get("priority", "medium"),
                tags=data.get("tags"),
                assignee_id=data.get("assignee_id"),
            )
            ticket = use_case.execute(input_data)
            return _ticket_to_dict(ticket), 201
        finally:
            session.close()


@tickets_ns.route("/<string:ticket_id>")
@tickets_ns.param("ticket_id", "Ticket ID")
class TicketDetail(Resource):
    """Single ticket endpoints."""

    @tickets_ns.doc("get_ticket")
    @tickets_ns.marshal_with(schemas["ticket_response"])
    @tickets_ns.response(404, "Ticket not found")
    def get(self, ticket_id):
        """Get a ticket by ID."""
        session = container.get_db_session()
        try:
            repo = container.ticket_repository(session)
            ticket = repo.get_by_id(ticket_id)
            if ticket is None:
                tickets_ns.abort(404, f"Ticket {ticket_id} not found")
            return _ticket_to_dict(ticket)
        finally:
            session.close()

    @tickets_ns.doc("update_ticket")
    @tickets_ns.expect(schemas["update_ticket"], validate=True)
    @tickets_ns.marshal_with(schemas["ticket_response"])
    @tickets_ns.response(404, "Ticket not found")
    @tickets_ns.response(409, "Ticket already closed")
    def put(self, ticket_id):
        """Update a ticket."""
        data = request.json
        session = container.get_db_session()
        try:
            use_case = UpdateTicketUseCase(
                ticket_repo=container.ticket_repository(session),
                search=container.search,
                broker=container.broker,
            )
            input_data = UpdateTicketInput(
                ticket_id=ticket_id,
                title=data.get("title"),
                description=data.get("description"),
                status=data.get("status"),
                priority=data.get("priority"),
                tags=data.get("tags"),
                assignee_id=data.get("assignee_id"),
            )
            ticket = use_case.execute(input_data)
            return _ticket_to_dict(ticket)
        finally:
            session.close()

    @tickets_ns.doc("delete_ticket")
    @tickets_ns.response(204, "Ticket deleted")
    @tickets_ns.response(404, "Ticket not found")
    def delete(self, ticket_id):
        """Delete a ticket."""
        session = container.get_db_session()
        try:
            repo = container.ticket_repository(session)
            deleted = repo.delete(ticket_id)
            if not deleted:
                tickets_ns.abort(404, f"Ticket {ticket_id} not found")
            try:
                container.search.delete_ticket(ticket_id)
            except Exception:
                pass
            return "", 204
        finally:
            session.close()


@tickets_ns.route("/<string:ticket_id>/close")
@tickets_ns.param("ticket_id", "Ticket ID")
class TicketClose(Resource):
    """Close a ticket."""

    @tickets_ns.doc("close_ticket")
    @tickets_ns.marshal_with(schemas["ticket_response"])
    @tickets_ns.response(404, "Ticket not found")
    @tickets_ns.response(409, "Ticket already closed")
    def post(self, ticket_id):
        """Close a ticket."""
        session = container.get_db_session()
        try:
            use_case = CloseTicketUseCase(
                ticket_repo=container.ticket_repository(session),
                search=container.search,
                broker=container.broker,
            )
            ticket = use_case.execute(ticket_id)
            return _ticket_to_dict(ticket)
        finally:
            session.close()


@tickets_ns.route("/<string:ticket_id>/comments")
@tickets_ns.param("ticket_id", "Ticket ID")
class TicketComments(Resource):
    """Ticket comment endpoints."""

    @tickets_ns.doc("list_comments")
    @tickets_ns.marshal_list_with(schemas["comment_response"])
    def get(self, ticket_id):
        """List comments for a ticket."""
        session = container.get_db_session()
        try:
            repo = container.comment_repository(session)
            comments = repo.get_by_ticket_id(ticket_id)
            return [_comment_to_dict(c) for c in comments]
        finally:
            session.close()

    @tickets_ns.doc("add_comment")
    @tickets_ns.expect(schemas["create_comment"], validate=True)
    @tickets_ns.marshal_with(schemas["comment_response"], code=201)
    def post(self, ticket_id):
        """Add a comment to a ticket."""
        data = request.json
        session = container.get_db_session()
        try:
            use_case = AddCommentUseCase(
                ticket_repo=container.ticket_repository(session),
                comment_repo=container.comment_repository(session),
            )
            input_data = AddCommentInput(
                ticket_id=ticket_id,
                author_id=data["author_id"],
                body=data["body"],
            )
            comment = use_case.execute(input_data)
            return _comment_to_dict(comment), 201
        finally:
            session.close()


@tickets_ns.route("/search")
class TicketSearch(Resource):
    """Full-text search endpoint."""

    @tickets_ns.doc("search_tickets")
    @tickets_ns.param("q", "Search query", required=True, type="string")
    @tickets_ns.param("status", "Filter by status", type="string")
    @tickets_ns.param("priority", "Filter by priority", type="string")
    @tickets_ns.param("assignee_id", "Filter by assignee", type="string")
    @tickets_ns.param("limit", "Max results (default: 20)", type="integer")
    @tickets_ns.marshal_list_with(schemas["search_result"])
    def get(self):
        """Search tickets using full-text search (Elasticsearch)."""
        session = container.get_db_session()
        try:
            use_case = SearchTicketsUseCase(
                ticket_repo=container.ticket_repository(session),
                search=container.search,
            )
            input_data = SearchTicketsInput(
                query=request.args.get("q", ""),
                status=request.args.get("status"),
                priority=request.args.get("priority"),
                assignee_id=request.args.get("assignee_id"),
                limit=int(request.args.get("limit", 20)),
            )
            results = use_case.execute(input_data)
            return results
        finally:
            session.close()
