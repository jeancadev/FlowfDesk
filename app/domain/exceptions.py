"""
FlowDesk Domain Exceptions — Business-specific error hierarchy.

Each exception carries context (IDs, relevant data) for meaningful
error handling and structured logging. Never use generic ValueError
or Exception for business logic.
"""


class DomainError(Exception):
    """Base class for all domain-level errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TicketNotFoundError(DomainError):
    """Raised when a ticket cannot be found by its ID."""

    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id
        super().__init__(
            message=f"Ticket not found: {ticket_id}",
            code="TICKET_NOT_FOUND",
        )


class TicketAlreadyClosedError(DomainError):
    """Raised when trying to modify a ticket that is already closed."""

    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id
        super().__init__(
            message=f"Ticket is already closed: {ticket_id}",
            code="TICKET_ALREADY_CLOSED",
        )


class UserNotFoundError(DomainError):
    """Raised when a user cannot be found."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(
            message=f"User not found: {user_id}",
            code="USER_NOT_FOUND",
        )


class InvalidTicketDataError(DomainError):
    """Raised when ticket data fails validation."""

    def __init__(self, details: str):
        super().__init__(
            message=f"Invalid ticket data: {details}",
            code="INVALID_TICKET_DATA",
        )


class AttachmentTooLargeError(DomainError):
    """Raised when an attachment exceeds the size limit."""

    MAX_SIZE_MB = 10

    def __init__(self, filename: str, size_bytes: int):
        self.filename = filename
        self.size_bytes = size_bytes
        super().__init__(
            message=(
                f"Attachment '{filename}' ({size_bytes} bytes) exceeds "
                f"{self.MAX_SIZE_MB}MB limit"
            ),
            code="ATTACHMENT_TOO_LARGE",
        )


class RateLimitExceededError(DomainError):
    """Raised when a client exceeds the rate limit."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        super().__init__(
            message=f"Rate limit exceeded for client: {client_id}",
            code="RATE_LIMIT_EXCEEDED",
        )
