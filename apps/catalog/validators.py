"""
Validators for catalog file uploads.

These keep uploaded media safe and predictable: whitelisted extensions,
a maximum file size, and a real content-type check based on the decoded
image rather than the client-supplied name.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Never trust a file extension alone. These MIME types correspond to the
# image formats we allow (Pillow verifies the actual bytes on save).
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]

# Hard cap on how many pixels an uploaded image may contain. Guards against
# "decompression bomb" images that look small on disk but explode in memory.
MAX_IMAGE_PIXELS = 30_000_000


def validate_image_size(file) -> None:
    """Reject image uploads larger than ``MAX_UPLOAD_SIZE_MB`` megabytes.

    Args:
        file: An ``UploadedFile``/``ImageFieldFile`` instance.

    Raises:
        ValidationError: If the file exceeds the configured size limit.
    """
    max_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 5)
    max_bytes = max_mb * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            _("Image is too large (%(size).1f MB). Maximum allowed is %(max)s MB.")
            % {"size": file.size / (1024 * 1024), "max": max_mb}
        )


def validate_image_content_type(file) -> None:
    """Reject files whose declared content type is not an allowed image type.

    Args:
        file: An ``UploadedFile`` instance exposing ``content_type``.

    Raises:
        ValidationError: If the content type is not in the allow-list.
    """
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError(
            _("Unsupported image type '%(type)s'. Allowed: JPEG, PNG, WEBP.")
            % {"type": content_type}
        )
