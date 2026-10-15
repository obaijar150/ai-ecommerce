"""
Tests for catalog upload validators (size and content type).
"""

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.catalog.validators import (
    validate_image_content_type,
    validate_image_size,
)


class TestImageValidators(TestCase):
    """Test the image size and content-type validators."""

    def test_small_file_passes_size_validation(self):
        """A small file passes the size check."""
        upload = SimpleUploadedFile("small.png", b"x" * 100)
        # Should not raise.
        validate_image_size(upload)

    @override_settings(MAX_UPLOAD_SIZE_MB=1)
    def test_large_file_fails_size_validation(self):
        """A file over the limit raises ValidationError."""
        upload = SimpleUploadedFile("big.png", b"x" * (2 * 1024 * 1024))
        with self.assertRaises(ValidationError):
            validate_image_size(upload)

    def test_allowed_content_type_passes(self):
        """An allowed MIME type passes."""
        upload = SimpleUploadedFile("a.png", b"x", content_type="image/png")
        validate_image_content_type(upload)

    def test_disallowed_content_type_fails(self):
        """A non-image MIME type raises ValidationError."""
        upload = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        with self.assertRaises(ValidationError):
            validate_image_content_type(upload)

    def test_missing_content_type_is_tolerated(self):
        """A file without a content type is not rejected (extension validates)."""
        upload = SimpleUploadedFile("a.png", b"x")
        upload.content_type = ""
        validate_image_content_type(upload)
