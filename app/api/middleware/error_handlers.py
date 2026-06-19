"""
API Middleware — Error handlers and rate limiting.

Centralizes error handling for domain exceptions and provides
Redis-based rate limiting.
"""

from flask import Flask, jsonify, request

from app.core.container import container
from app.core.logging import get_logger
from app.domain.exceptions import (
    AttachmentTooLargeError,
    DomainError,
    InvalidTicketDataError,
    RateLimitExceededError,
    TicketAlreadyClosedError,
    TicketNotFoundError,
    UserNotFoundError,
)

logger = get_logger(__name__)

# ─── Error Code → HTTP Status Mapping ────────────────────────────────

ERROR_STATUS_MAP = {
    TicketNotFoundError: 404,
    UserNotFoundError: 404,
    TicketAlreadyClosedError: 409,
    InvalidTicketDataError: 400,
    AttachmentTooLargeError: 413,
    RateLimitExceededError: 429,
}


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for domain exceptions."""

    @app.errorhandler(DomainError)
    def handle_domain_error(error: DomainError):
        status_code = ERROR_STATUS_MAP.get(type(error), 400)
        logger.warning(
            "domain_error",
            error_code=error.code,
            message=error.message,
            status_code=status_code,
        )
        return jsonify(
            {
                "error": error.message,
                "code": error.code,
            }
        ), status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify(
            {
                "error": "Resource not found",
                "code": "NOT_FOUND",
            }
        ), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error("internal_server_error", error=str(error))
        return jsonify(
            {
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
            }
        ), 500


def register_rate_limiting(app: Flask) -> None:
    """Register rate limiting middleware using Redis."""

    @app.before_request
    def check_rate_limit():
        # Skip rate limiting for Swagger docs
        if request.path.startswith("/swagger") or request.path == "/":
            return

        client_ip = request.remote_addr or "unknown"
        key = f"rate_limit:{client_ip}"

        try:
            from app.core.config import get_settings

            settings = get_settings()
            count = container.cache.increment(key, ttl_seconds=60)

            if count > settings.RATE_LIMIT_PER_MINUTE:
                logger.warning("rate_limit_exceeded", client_ip=client_ip, count=count)
                return jsonify(
                    {
                        "error": "Rate limit exceeded. Try again later.",
                        "code": "RATE_LIMIT_EXCEEDED",
                    }
                ), 429
        except Exception:
            pass  # If Redis is down, allow the request through
