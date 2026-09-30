"""Image uploads for article and event artwork.

Files are written to a directory on disk and served back as static files. Deliberately
simple: the alternative is an object store, which means credentials, a bucket policy and a
second thing to configure before anyone can add a picture to an article.

Three rules matter here, and all three are about not trusting the client:

1. The stored filename is generated, never taken from the upload. A name like
   ``../../app/main.py`` is otherwise a path traversal, and a name like ``x.html`` served
   from our own origin is a stored cross-site scripting vector.
2. The type is decided by the file's own leading bytes, not by its extension or the
   declared content type, both of which the caller controls.
3. Size is capped while reading rather than after, so a large upload is refused before it
   has been written anywhere.
"""

import uuid
from pathlib import Path

# 8 MB. Large enough for a photograph off a phone, small enough that a handful of them do
# not fill the volume.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024

# Magic bytes are how the format is actually identified. The extension we append is ours.
_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
]

UPLOAD_DIR = Path("uploads")
# The path the browser requests. Kept distinct from the disk path so one can move without
# the other.
UPLOAD_URL_PREFIX = "/uploads"


def detect_extension(head: bytes) -> str | None:
    """The file extension implied by the leading bytes, or None if unrecognised."""
    for signature, extension in _SIGNATURES:
        if head.startswith(signature):
            return extension

    # WebP is RIFF-framed: "RIFF", four bytes of length, then "WEBP".
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"

    return None


def build_stored_name(extension: str) -> str:
    """A safe, unique filename. Never derived from anything the caller sent."""
    return f"{uuid.uuid4().hex}{extension}"


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR
