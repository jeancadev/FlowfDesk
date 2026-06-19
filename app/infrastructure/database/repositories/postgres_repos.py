"""
PostgreSQL Repository Implementations.

Concrete implementations of domain ports using SQLAlchemy.
These adapters translate between domain entities and ORM models.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.entities.ticket import (
    Attachment,
    Comment,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
    UserRole,
)
from app.infrastructure.database.models import (
    AttachmentModel,
    CommentModel,
    TicketModel,
    UserModel,
)

# ─── Mapper Helpers ──────────────────────────────────────────────────


def _ticket_model_to_entity(model: TicketModel) -> Ticket:
    """Convert ORM model to domain entity."""
    return Ticket(
        id=model.id,
        title=model.title,
        description=model.description,
        status=TicketStatus(model.status),
        priority=TicketPriority(model.priority),
        tags=model.tags or [],
        creator_id=model.creator_id,
        assignee_id=model.assignee_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        closed_at=model.closed_at,
    )


def _user_model_to_entity(model: UserModel) -> User:
    """Convert ORM model to domain entity."""
    return User(
        id=model.id,
        email=model.email,
        full_name=model.full_name,
        role=UserRole(model.role),
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _comment_model_to_entity(model: CommentModel) -> Comment:
    return Comment(
        id=model.id,
        ticket_id=model.ticket_id,
        author_id=model.author_id,
        body=model.body,
        created_at=model.created_at,
    )


def _attachment_model_to_entity(model: AttachmentModel) -> Attachment:
    return Attachment(
        id=model.id,
        ticket_id=model.ticket_id,
        filename=model.filename,
        content_type=model.content_type,
        size_bytes=model.size_bytes,
        s3_key=model.s3_key,
        uploaded_by=model.uploaded_by,
        uploaded_at=model.uploaded_at,
    )


# ─── Ticket Repository ──────────────────────────────────────────────


class PostgresTicketRepository:
    """PostgreSQL implementation of TicketRepository port."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, ticket: Ticket) -> Ticket:
        model = TicketModel(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status.value,
            priority=ticket.priority.value,
            tags=ticket.tags,
            creator_id=ticket.creator_id,
            assignee_id=ticket.assignee_id,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            closed_at=ticket.closed_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _ticket_model_to_entity(model)

    def get_by_id(self, ticket_id: str) -> Ticket | None:
        model = self._session.get(TicketModel, ticket_id)
        return _ticket_model_to_entity(model) if model else None

    def list_all(
        self,
        status: str | None = None,
        assignee_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Ticket]:
        query = self._session.query(TicketModel)
        if status:
            query = query.filter(TicketModel.status == status)
        if assignee_id:
            query = query.filter(TicketModel.assignee_id == assignee_id)
        query = query.order_by(TicketModel.created_at.desc())
        models = query.offset(offset).limit(limit).all()
        return [_ticket_model_to_entity(m) for m in models]

    def update(self, ticket: Ticket) -> Ticket:
        model = self._session.get(TicketModel, ticket.id)
        if model is None:
            raise ValueError(f"Ticket {ticket.id} not found for update")
        model.title = ticket.title
        model.description = ticket.description
        model.status = ticket.status.value
        model.priority = ticket.priority.value
        model.tags = ticket.tags
        model.assignee_id = ticket.assignee_id
        model.updated_at = ticket.updated_at
        model.closed_at = ticket.closed_at
        self._session.commit()
        self._session.refresh(model)
        return _ticket_model_to_entity(model)

    def delete(self, ticket_id: str) -> bool:
        model = self._session.get(TicketModel, ticket_id)
        if model is None:
            return False
        self._session.delete(model)
        self._session.commit()
        return True

    def count(
        self,
        status: str | None = None,
        assignee_id: str | None = None,
    ) -> int:
        query = self._session.query(TicketModel)
        if status:
            query = query.filter(TicketModel.status == status)
        if assignee_id:
            query = query.filter(TicketModel.assignee_id == assignee_id)
        return query.count()


# ─── User Repository ────────────────────────────────────────────────


class PostgresUserRepository:
    """PostgreSQL implementation of UserRepository port."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _user_model_to_entity(model)

    def get_by_id(self, user_id: str) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _user_model_to_entity(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = self._session.query(UserModel).filter_by(email=email).first()
        return _user_model_to_entity(model) if model else None

    def list_all(self, limit: int = 50, offset: int = 0) -> list[User]:
        models = (
            self._session.query(UserModel)
            .order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_user_model_to_entity(m) for m in models]


# ─── Comment Repository ─────────────────────────────────────────────


class PostgresCommentRepository:
    """PostgreSQL implementation of CommentRepository port."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, comment: Comment) -> Comment:
        model = CommentModel(
            id=comment.id,
            ticket_id=comment.ticket_id,
            author_id=comment.author_id,
            body=comment.body,
            created_at=comment.created_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _comment_model_to_entity(model)

    def get_by_ticket_id(self, ticket_id: str) -> list[Comment]:
        models = (
            self._session.query(CommentModel)
            .filter_by(ticket_id=ticket_id)
            .order_by(CommentModel.created_at.asc())
            .all()
        )
        return [_comment_model_to_entity(m) for m in models]


# ─── Attachment Repository ───────────────────────────────────────────


class PostgresAttachmentRepository:
    """PostgreSQL implementation of AttachmentRepository port."""

    def __init__(self, session: Session):
        self._session = session

    def save(self, attachment: Attachment) -> Attachment:
        model = AttachmentModel(
            id=attachment.id,
            ticket_id=attachment.ticket_id,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size_bytes=attachment.size_bytes,
            s3_key=attachment.s3_key,
            uploaded_by=attachment.uploaded_by,
            uploaded_at=attachment.uploaded_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return _attachment_model_to_entity(model)

    def get_by_ticket_id(self, ticket_id: str) -> list[Attachment]:
        models = (
            self._session.query(AttachmentModel)
            .filter_by(ticket_id=ticket_id)
            .order_by(AttachmentModel.uploaded_at.desc())
            .all()
        )
        return [_attachment_model_to_entity(m) for m in models]
