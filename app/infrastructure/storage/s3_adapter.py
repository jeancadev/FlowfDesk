"""
S3 Storage Adapter — Implementation of StoragePort.

Handles file uploads and presigned URL generation for ticket attachments.
Compatible with AWS S3 and MinIO (for local development).
"""

from __future__ import annotations

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class S3StorageAdapter:
    """S3/MinIO implementation of the StoragePort interface."""

    def __init__(self):
        settings = get_settings()
        self._bucket = settings.AWS_S3_BUCKET
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=BotoConfig(signature_version="s3v4"),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the S3 bucket if it doesn't exist."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self._bucket)
                logger.info("s3_bucket_created", bucket=self._bucket)
            except ClientError as e:
                logger.warning("s3_bucket_creation_failed", error=str(e))

    def upload(
        self,
        file_data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file to S3 and return the key."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=file_data,
            ContentType=content_type,
        )
        logger.info("s3_file_uploaded", key=key, size=len(file_data))
        return key

    def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate a presigned URL for downloading a file."""
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiration,
        )
        return url

    def delete(self, key: str) -> None:
        """Delete a file from S3."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("s3_file_deleted", key=key)
        except ClientError as e:
            logger.error("s3_delete_failed", key=key, error=str(e))
