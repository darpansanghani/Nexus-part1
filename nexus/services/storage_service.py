"""Google Cloud Storage service for NEXUS image handling."""

import datetime
import io
import logging
import uuid
from typing import Optional, Tuple
from flask import Flask
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError
from PIL import Image

from exceptions import StorageError, ValidationError

logger = logging.getLogger("nexus-app.storage-service")

class StorageService:
    """Manages secure image validation, processing, and GCS uploads."""

    def __init__(self) -> None:
        self._client: storage.Client | None = None
        self._bucket_name: str = "nexus-uploads"
        self._testing: bool = False
        self._mock_db: dict[str, bytes] = {}

    def init_app(self, app: Flask) -> None:
        """Initialize the Storage client."""
        self._testing = app.config.get("TESTING", False)
        self._bucket_name = app.config.get("GCS_BUCKET_NAME", "nexus-uploads")
        
        if not self._testing:
            try:
                project_id = app.config.get("GCP_PROJECT_ID")
                self._client = storage.Client(project=project_id)
                logger.info("Storage client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Storage client: {e}", exc_info=True)
        else:
            logger.info("Using mock Storage for testing.")

    def process_and_upload_image(self, file_bytes: bytes) -> Tuple[str, bytes]:
        """Process an image (resize, strip EXIF, convert to JPEG) and upload to GCS.
        
        Args:
            file_bytes: Raw bytes of the uploaded image
            
        Returns:
            Tuple of (signed URL, processed image bytes)
            
        Raises:
            ValidationError: If the image is invalid or cannot be processed
            StorageError: If the upload to GCS fails
        """
        # 1. Process image with Pillow (strips EXIF implicitly when saving without exif data)
        try:
            image = Image.open(io.BytesIO(file_bytes))
            
            # Convert to RGB if necessary (e.g., from RGBA or raw formats)
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Resize if larger than 2048x2048, maintaining aspect ratio
            max_size = (2048, 2048)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to a new byte stream as JPEG quality=85
            output_buffer = io.BytesIO()
            image.save(output_buffer, format="JPEG", quality=85, optimize=True)
            processed_bytes = output_buffer.getvalue()
        except Exception as e:
            logger.error(f"Image processing failed: {e}")
            raise ValidationError(f"Invalid image data: {str(e)}")

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
            # For this to work, the service account needs the Service Account Token Creator role
            try:
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=datetime.timedelta(hours=1),
                    method="GET"
                )
            except Exception as e:
                # If local creds can't sign URLs, fallback to returning the blob path
                logger.warning(f"Could not generate signed URL: {e}")
                signed_url = f"gs://{self._bucket_name}/{filename}"
                
            return signed_url, processed_bytes
        except GoogleAPIError as e:
            logger.error(f"Failed to upload to GCS: {e}", exc_info=True)
            raise StorageError(f"Upload failed: {str(e)}")

# Singleton instance
storage_service = StorageService()

def init_app(app: Flask) -> None:
    storage_service.init_app(app)
