
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


class ObjectStorageService:
    """S3-compatible object storage client for Silo."""

    def __init__(self):
        settings = get_settings()

        self.bucket_name = settings.S3_BUCKET_NAME

        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not exist."""

        buckets = self.client.list_buckets()["Buckets"]

        exists = any(
            bucket["Name"] == self.bucket_name
            for bucket in buckets
        )

        if not exists:
            self.client.create_bucket(Bucket=self.bucket_name)

    def upload_file(
        self,
        file_path: str | Path,
        object_key: str,
        content_type: str | None = None,
    ) -> str:
        """Upload a local file to object storage."""

        extra_args = {}

        if content_type:
            extra_args["ContentType"] = content_type

        self.client.upload_file(
            str(file_path),
            self.bucket_name,
            object_key,
            ExtraArgs=extra_args or None,
        )

        return object_key

    def upload_bytes(
        self,
        content: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes directly to object storage."""

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )

        return object_key

    def download_file(
        self,
        object_key: str,
        destination: str | Path,
    ) -> Path:
        """Download an object to a local file."""

        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        self.client.download_file(
            self.bucket_name,
            object_key,
            str(destination),
        )

        return destination

    def read_bytes(self, object_key: str) -> bytes:
        """Read an object into memory."""

        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=object_key,
        )

        try:
            return response["Body"].read()
        finally:
            response["Body"].close()

    def exists(self, object_key: str) -> bool:
        """Check whether an object exists."""
    
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key,
            )
            return True
    
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                return False
            raise

    def delete(self, object_key: str) -> None:
        """Delete an object."""

        self.client.delete_object(
            Bucket=self.bucket_name,
            Key=object_key,
        )
