
import hashlib
import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database.models import DocumentRecord
from app.storage import ObjectStorageService


CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}


def create_slug(value: str) -> str:
    """Convert a name into a safe storage path component."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return slug.strip("-")


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 checksum without loading the whole file."""

    checksum = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            checksum.update(chunk)

    return checksum.hexdigest()


class DocumentRegistrationService:

    def __init__(self):
        self.storage = ObjectStorageService()

    def register(
        self,
        db: Session,
        file_path: str | Path,
        insurer: str,
        product_line: str,
        document_type: str,
        version: str,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> DocumentRecord:
        """Store the original document and register its metadata."""

        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"Document not found: {path}")

        extension = path.suffix.lower()

        if extension not in CONTENT_TYPES:
            raise ValueError(
                f"Unsupported document format: {extension}"
            )

        if effective_from and effective_to:
            if effective_to < effective_from:
                raise ValueError(
                    "effective_to cannot be earlier than effective_from."
                )

        checksum = calculate_sha256(path)
        document_id = uuid4()

        insurer_slug = create_slug(insurer)
        product_slug = create_slug(product_line)
        filename = re.sub(r"[^a-zA-Z0-9._-]", "_", path.name)

        object_key = (
            f"insurers/{insurer_slug}/{product_slug}/"
            f"{version}/{document_id}_{filename}"
        )

        content_type = CONTENT_TYPES[extension]

        self.storage.ensure_bucket()

        # Upload the original file first.
        self.storage.upload_file(
            file_path=path,
            object_key=object_key,
            content_type=content_type,
        )

        record = DocumentRecord(
            id=document_id,
            insurer=insurer,
            product_line=product_line,
            document_type=document_type,
            original_filename=path.name,
            object_key=object_key,
            content_type=content_type,
            file_size=path.stat().st_size,
            checksum_sha256=checksum,
            version=version,
            effective_from=effective_from,
            effective_to=effective_to,
            status="registered",
        )

        try:
            db.add(record)
            db.commit()
            db.refresh(record)

            return record

        except Exception:
            db.rollback()

            # Avoid leaving an unregistered file in object storage.
            self.storage.delete(object_key)
            raise
