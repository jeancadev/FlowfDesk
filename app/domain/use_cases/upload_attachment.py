"""
Use Case: Upload Attachment

Handles file upload to S3 and persists metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.domain.entities.ticket import Attachment, TicketStatus
from app.domain.exceptions import (
    AttachmentTooLargeError,
    TicketAlreadyClosedError,
    TicketNotFoundError,
)
from app.domain.ports.repositories import (
    AttachmentRepository,
    StoragePort,
    TicketRepository,
)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@dataclass
class UploadAttachmentInput:
    """Input DTO for uploading an attachment."""

    ticket_id: str
    filename: str
    content_type: str
    file_data: bytes
    uploaded_by: str


class UploadAttachmentUseCase:
    """Uploads a file to S3 and saves attachment metadata."""

    def __init__(
        self,
        ticket_repo: TicketRepository,
        attachment_repo: AttachmentRepository,
        storage: StoragePort,
    ):
        self._ticket_repo = ticket_repo
        self._attachment_repo = attachment_repo
        self._storage = storage

    def execute(self, input_data: UploadAttachmentInput) -> Attachment:
        # ── Validate ticket ──
        ticket = self._ticket_repo.get_by_id(input_data.ticket_id)
        if ticket is None:
            raise TicketNotFoundError(input_data.ticket_id)

        if ticket.status == TicketStatus.CLOSED:
            raise TicketAlreadyClosedError(input_data.ticket_id)

        # ── Validate file size ──
        size = len(input_data.file_data)
        if size > MAX_FILE_SIZE_BYTES:
            raise AttachmentTooLargeError(input_data.filename, size)

        # ── Upload to storage ──
        s3_key = f"tickets/{input_data.ticket_id}/{uuid.uuid4()}/{input_data.filename}"
        self._storage.upload(
            file_data=input_data.file_data,
            key=s3_key,
            content_type=input_data.content_type,
        )

        # ── Persist metadata ──
        attachment = Attachment(
            ticket_id=input_data.ticket_id,
            filename=input_data.filename,
            content_type=input_data.content_type,
            size_bytes=size,
            s3_key=s3_key,
            uploaded_by=input_data.uploaded_by,
        )

        return self._attachment_repo.save(attachment)
