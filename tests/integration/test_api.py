"""
Integration Tests — API Endpoints.

Tests the full Flask API endpoints with mocked infrastructure.
These tests verify the HTTP layer: routes, status codes, payloads, and error responses.
"""

import json


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "flowdesk-api"

    def test_health_includes_redis_status(self, client):
        response = client.get("/health")
        data = response.get_json()
        assert "redis" in data


class TestTicketEndpoints:
    """Tests for ticket API endpoints."""

    def _create_user_and_ticket(self, client):
        """Helper: create a user then a ticket via API."""
        # Create a user first
        user_resp = client.post(
            "/api/v1/users/",
            data=json.dumps(
                {
                    "email": "testuser@flowdesk.io",
                    "full_name": "Test User",
                    "role": "agent",
                }
            ),
            content_type="application/json",
        )
        user_data = user_resp.get_json()
        user_id = user_data.get("id", "test-user-id")

        # Create a ticket
        ticket_resp = client.post(
            "/api/v1/tickets/",
            data=json.dumps(
                {
                    "title": "API Test Ticket",
                    "description": (
                        "This is a test ticket created from the API "
                        "integration tests."
                    ),
                    "creator_id": user_id,
                    "priority": "high",
                    "tags": ["test", "api"],
                }
            ),
            content_type="application/json",
        )
        return user_id, ticket_resp

    def test_create_ticket_returns_201(self, client):
        _, response = self._create_user_and_ticket(client)
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "API Test Ticket"
        assert data["status"] == "open"
        assert data["priority"] == "high"

    def test_create_ticket_missing_title_returns_400(self, client):
        response = client.post(
            "/api/v1/tickets/",
            data=json.dumps(
                {
                    "description": "No title provided here.",
                    "creator_id": "user-001",
                }
            ),
            content_type="application/json",
        )
        # Flask-RESTX validates required fields
        assert response.status_code == 400

    def test_get_ticket_not_found_returns_404(self, client):
        response = client.get("/api/v1/tickets/nonexistent-ticket-id")
        assert response.status_code == 404

    def test_list_tickets_returns_200(self, client):
        response = client.get("/api/v1/tickets/")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)


class TestUserEndpoints:
    """Tests for user API endpoints."""

    def test_create_user_returns_201(self, client):
        response = client.post(
            "/api/v1/users/",
            data=json.dumps(
                {
                    "email": "newuser@flowdesk.io",
                    "full_name": "New User",
                    "role": "customer",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["email"] == "newuser@flowdesk.io"
        assert data["role"] == "customer"

    def test_create_user_missing_email_returns_400(self, client):
        response = client.post(
            "/api/v1/users/",
            data=json.dumps(
                {
                    "full_name": "No Email User",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_list_users_returns_200(self, client):
        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

    def test_get_user_not_found_returns_404(self, client):
        response = client.get("/api/v1/users/nonexistent-user-id")
        assert response.status_code == 404


class TestSwaggerDocs:
    """Verify Swagger documentation is accessible."""

    def test_swagger_ui_accessible(self, client):
        response = client.get("/swagger/")
        assert response.status_code == 200

    def test_swagger_json_accessible(self, client):
        response = client.get("/swagger.json")
        assert response.status_code == 200
        data = response.get_json()
        assert "info" in data
        assert data["info"]["title"] == "FlowDesk API"
