"""
FlowDesk Application Factory.

Creates and configures the Flask application with all extensions,
routes, and middleware. Follows the Application Factory pattern.
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from flask_restx import Api

from app.api.middleware.error_handlers import (
    register_error_handlers,
    register_rate_limiting,
)
from app.api.v1.routes.tickets import tickets_ns
from app.api.v1.routes.users import users_ns
from app.core.config import get_settings
from app.core.logging import setup_logging


def create_app(testing: bool = False) -> Flask:
    """
    Flask Application Factory.

    Creates the Flask app, configures extensions, registers routes,
    and sets up middleware.

    Args:
        testing: If True, uses test configuration.

    Returns:
        Configured Flask application instance.
    """
    # â”€â”€ Load settings â”€â”€
    settings = get_settings()

    # â”€â”€ Setup logging â”€â”€
    log_level = "DEBUG" if settings.FLASK_DEBUG else "INFO"
    setup_logging(log_level)

    # â”€â”€ Create Flask app â”€â”€
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["TESTING"] = testing

    # â”€â”€ CORS â”€â”€
    CORS(app)

    @app.get("/")
    def web_app():
        """Serve the FlowDesk operator UI."""
        return render_template("index.html")

    # â”€â”€ Flask-RESTX API â”€â”€
    api = Api(
        app,
        version="1.0",
        title="FlowDesk API",
        description=(
            "Internal ticket management and support system "
            "with intelligent search powered by Elasticsearch "
            "and real-time events via Kafka."
        ),
        doc="/swagger/",
        prefix="",
    )

    # â”€â”€ Register namespaces â”€â”€
    api.add_namespace(tickets_ns)
    api.add_namespace(users_ns)

    # â”€â”€ Register middleware â”€â”€
    register_error_handlers(app)
    register_rate_limiting(app)

    # â”€â”€ Health check endpoint â”€â”€
    @app.route("/health")
    def health():
        """Health check endpoint for Docker/Kubernetes."""
        health_status = {
            "status": "healthy",
            "service": "flowdesk-api",
            "version": "0.1.0",
        }

        # Check Redis
        try:
            from app.core.container import container

            health_status["redis"] = (
                "connected" if container.cache.ping() else "disconnected"
            )
        except Exception:
            health_status["redis"] = "disconnected"

        return jsonify(health_status)

    return app


