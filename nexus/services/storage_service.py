"""Google Cloud Storage service for NEXUS image handling."""

import datetime
import io
import uuid

from flask import Flask
from google.api_core.exceptions import GoogleAPIError
from google.cloud import storage
from PIL import Image

from exceptions import StorageError, ValidationError
from logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """Manages secure image validation, processing, and GCS uploads."""

    def __init__(self) -> None:
        """Initialize the StorageService."""
        self._client: storage.Client | None = None
        self._bucket_name: str = "nexus-uploads"
        self._testing: bool = False
        self._mock_db: dict[str, bytes] = {}

    def init_app(self, app: Flask) -> None:
        """Initialize the Storage client.

        Args:
            app: The Flask application instance.
        """
        self._testing = app.config.get("TESTING", False)
        self._bucket_name = app.config.get("GCS_BUCKET_NAME", "nexus-uploads")

        if not self._testing:
            try:
                project_id = app.config.get("GCP_PROJECT_ID")
                self._client = storage.Client(project=project_id)
                logger.info("Storage client initialized successfully.")
            except Exception:
                logger.exception("Failed to initialize Storage client")
        else:
            logger.info("Using mock Storage for testing.")

    def process_and_upload_image(self, file_bytes: bytes) -> tuple[str, bytes]:
        """Process an image (resize, strip EXIF, convert to JPEG) and upload to GCS.

        Args:
            file_bytes: Raw bytes of the uploaded image.

        Returns:
            Tuple of (signed URL, processed image bytes).

        Raises:
            ValidationError: If the image is invalid or cannot be processed.
            StorageError: If the upload to GCS fails.
        """
        # 1. Process image with Pillow (strips EXIF implicitly when saving without exif data)
        try:
            image = Image.open(io.BytesIO(file_bytes))

            # Convert to RGB if necessary (e.g., from RGBA or raw formats)
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Resize if larger than 2048x2048, maintaining aspect ratio
            max_size: tuple[int, int] = (2048, 2048)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)  # type: ignore[no-untyped-call]

            # Save to a new byte stream as JPEG quality=85
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="JPEG", quality=85, optimize=True)
            processed_bytes: bytes = output_buffer.getvalue()
        except Exception as e:
            logger.exception("Image processing failed")
            raise ValidationError("Invalid image data.") from e

        # 2. Upload to GCS
        filename = f"{uuid.uuid4().hex}.jpg"

        if self._testing:
            self._mock_db[filename] = processed_bytes
            return f"https://mock-storage.local/{self._bucket_name}/{filename}", processed_bytes

        if self._client is None:
            raise StorageError("Storage client not initialized")

        try:
            bucket = self._client.bucket(self._bucket_name)
            blob = bucket.blob(filename)
            blob.upload_from_string(processed_bytes, content_type="image/jpeg")

            # Generate signed URL valid for 1 hour for secure retrieval
            try:
                signed_url: str = blob.generate_signed_url(
                    version="v4", expiration=datetime.timedelta(hours=1), method="GET"
                )
            except Exception:
                # If local creds can't sign URLs, fallback to returning the blob path
                logger.exception("Could not generate signed URL")
                signed_url = f"gs://{self._bucket_name}/{filename}"

            return signed_url, processed_bytes
        except GoogleAPIError as e:
            logger.exception("Failed to upload to GCS")
            raise StorageError("Upload failed") from e


# Singleton instance
storage_service = StorageService()


def init_app(app: Flask) -> None:
    """Initialize the global Storage instance.

    Args:
        app: The Flask app instance.
    """
    storage_service.init_app(app)
