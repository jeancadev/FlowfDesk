"""
Flask-RESTX API Models — Request/Response schemas for Swagger documentation.

These define the shape of data going in and out of the API.
They provide automatic Swagger documentation and request validation.
"""

from flask_restx import fields


def register_ticket_schemas(api):
    """Register all ticket-related API models with the Flask-RESTX API."""

    # ── Request Models ──

    create_ticket_model = api.model(
        "CreateTicket",
        {
            "title": fields.String(
                required=True,
                description="Ticket title (min 3 characters)",
                example="Login page returns 500 error",
                min_length=3,
            ),
            "description": fields.String(
                required=True,
                description="Detailed description of the issue (min 10 characters)",
                example=(
                    "When clicking the login button with valid credentials, "
                    "the server returns a 500 error. This started happening "
                    "after the last deployment."
                ),
                min_length=10,
            ),
            "priority": fields.String(
                description="Ticket priority level",
                enum=["low", "medium", "high", "critical"],
                default="medium",
            ),
            "tags": fields.List(
                fields.String,
                description="Tags for categorization",
                example=["bug", "auth", "production"],
            ),
            "creator_id": fields.String(
                required=True,
                description="ID of the user creating the ticket",
            ),
            "assignee_id": fields.String(
                description="ID of the agent to assign",
            ),
        },
    )

    update_ticket_model = api.model(
        "UpdateTicket",
        {
            "title": fields.String(description="New title"),
            "description": fields.String(description="New description"),
            "status": fields.String(
                description="New status",
                enum=[
                    "open",
                    "in_progress",
                    "waiting_on_customer",
                    "resolved",
                    "closed",
                ],
            ),
            "priority": fields.String(
                description="New priority",
                enum=["low", "medium", "high", "critical"],
            ),
            "tags": fields.List(fields.String, description="New tags"),
            "assignee_id": fields.String(description="New assignee ID"),
        },
    )

    # ── Response Models ──

    ticket_response_model = api.model(
        "TicketResponse",
        {
            "id": fields.String(description="Unique ticket ID"),
            "title": fields.String(description="Ticket title"),
            "description": fields.String(description="Ticket description"),
            "status": fields.String(description="Current status"),
            "priority": fields.String(description="Priority level"),
            "tags": fields.List(fields.String, description="Tags"),
            "creator_id": fields.String(description="Creator user ID"),
            "assignee_id": fields.String(description="Assignee user ID"),
            "created_at": fields.String(description="Creation timestamp (ISO 8601)"),
            "updated_at": fields.String(description="Last update timestamp (ISO 8601)"),
            "closed_at": fields.String(description="Closure timestamp (ISO 8601)"),
        },
    )

    ticket_list_response = api.model(
        "TicketListResponse",
        {
            "tickets": fields.List(fields.Nested(ticket_response_model)),
            "total": fields.Integer(description="Total count"),
            "limit": fields.Integer(description="Items per page"),
            "offset": fields.Integer(description="Offset"),
        },
    )

    # ── Comment Models ──

    create_comment_model = api.model(
        "CreateComment",
        {
            "author_id": fields.String(required=True, description="Comment author ID"),
            "body": fields.String(required=True, description="Comment text"),
        },
    )

    comment_response_model = api.model(
        "CommentResponse",
        {
            "id": fields.String(description="Comment ID"),
            "ticket_id": fields.String(description="Parent ticket ID"),
            "author_id": fields.String(description="Author user ID"),
            "body": fields.String(description="Comment body"),
            "created_at": fields.String(description="Creation timestamp"),
        },
    )

    # ── Search Models ──

    search_result_model = api.model(
        "SearchResult",
        {
            "id": fields.String(description="Ticket ID"),
            "title": fields.String(description="Ticket title"),
            "description": fields.String(description="Ticket description"),
            "status": fields.String(description="Status"),
            "priority": fields.String(description="Priority"),
            "creator_id": fields.String(description="Creator ID"),
            "created_at": fields.String(description="Creation timestamp"),
            "_score": fields.Float(description="Relevance score"),
        },
    )

    # ── User Models ──

    create_user_model = api.model(
        "CreateUser",
        {
            "email": fields.String(required=True, description="User email"),
            "full_name": fields.String(required=True, description="Full name"),
            "role": fields.String(
                description="User role",
                enum=["agent", "admin", "customer"],
                default="customer",
            ),
        },
    )

    user_response_model = api.model(
        "UserResponse",
        {
            "id": fields.String(description="User ID"),
            "email": fields.String(description="Email"),
            "full_name": fields.String(description="Full name"),
            "role": fields.String(description="Role"),
            "is_active": fields.Boolean(description="Active status"),
            "created_at": fields.String(description="Creation timestamp"),
        },
    )

    return {
        "create_ticket": create_ticket_model,
        "update_ticket": update_ticket_model,
        "ticket_response": ticket_response_model,
        "ticket_list": ticket_list_response,
        "create_comment": create_comment_model,
        "comment_response": comment_response_model,
        "search_result": search_result_model,
        "create_user": create_user_model,
        "user_response": user_response_model,
    }
