"""
User Routes — Flask-RESTX namespace for user management.
"""

from flask import request
from flask_restx import Namespace, Resource

from app.api.v1.schemas.ticket_schemas import register_ticket_schemas
from app.core.container import container
from app.domain.entities.ticket import User, UserRole

users_ns = Namespace(
    "users",
    description="User management operations",
    path="/api/v1/users",
)

schemas = register_ticket_schemas(users_ns)


def _user_to_dict(user):
    """Serialize a User entity to dict."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@users_ns.route("/")
class UserList(Resource):
    """User collection endpoints."""

    @users_ns.doc("list_users")
    @users_ns.marshal_list_with(schemas["user_response"])
    def get(self):
        """List all users."""
        session = container.get_db_session()
        try:
            repo = container.user_repository(session)
            users = repo.list_all()
            return [_user_to_dict(u) for u in users]
        finally:
            session.close()

    @users_ns.doc("create_user")
    @users_ns.expect(schemas["create_user"], validate=True)
    @users_ns.marshal_with(schemas["user_response"], code=201)
    def post(self):
        """Create a new user."""
        data = request.json
        session = container.get_db_session()
        try:
            repo = container.user_repository(session)

            # Check if email already exists
            existing = repo.get_by_email(data["email"])
            if existing:
                users_ns.abort(409, f"User with email {data['email']} already exists")

            try:
                role = UserRole(data.get("role", "customer"))
            except ValueError:
                users_ns.abort(400, f"Invalid role: {data.get('role')}")

            user = User(
                email=data["email"],
                full_name=data["full_name"],
                role=role,
            )
            saved = repo.save(user)
            return _user_to_dict(saved), 201
        finally:
            session.close()


@users_ns.route("/<string:user_id>")
@users_ns.param("user_id", "User ID")
class UserDetail(Resource):
    """Single user endpoints."""

    @users_ns.doc("get_user")
    @users_ns.marshal_with(schemas["user_response"])
    @users_ns.response(404, "User not found")
    def get(self, user_id):
        """Get a user by ID."""
        session = container.get_db_session()
        try:
            repo = container.user_repository(session)
            user = repo.get_by_id(user_id)
            if user is None:
                users_ns.abort(404, f"User {user_id} not found")
            return _user_to_dict(user)
        finally:
            session.close()
