import asyncio
import uuid
from pathlib import Path

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
ALLOWED_RESUME_CONTENT_TYPES = {"application/pdf": ".pdf"}


def get_upload_root() -> Path:
    root = Path(get_settings().UPLOAD_DIR)
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_public_url(relative_path: str) -> str:
    return f"/uploads/{relative_path.replace(chr(92), '/')}"


def _validate_size(content: bytes, max_bytes: int, label: str) -> None:
    if len(content) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{label} must be at most {max_mb} MB",
        )


def _configure_cloudinary() -> None:
    settings = get_settings()
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def _cloudinary_folder(category: str, owner_id: uuid.UUID) -> str:
    settings = get_settings()
    return f"{settings.CLOUDINARY_FOLDER}/{category}/{owner_id}"


def _upload_bytes_to_cloudinary(
    content: bytes,
    *,
    folder: str,
    resource_type: str,
) -> str:
    _configure_cloudinary()
    result = cloudinary.uploader.upload(
        content,
        folder=folder,
        resource_type=resource_type,
        public_id=str(uuid.uuid4()),
        overwrite=False,
    )
    return result["secure_url"]


async def _upload_bytes_to_cloudinary_async(
    content: bytes,
    *,
    folder: str,
    resource_type: str,
) -> str:
    return await asyncio.to_thread(
        _upload_bytes_to_cloudinary,
        content,
        folder=folder,
        resource_type=resource_type,
    )


def _cloudinary_target_from_url(url: str) -> tuple[str, str] | None:
    if "res.cloudinary.com" not in url:
        return None

    if "/image/upload/" in url:
        resource_type = "image"
        suffix = url.split("/image/upload/", 1)[1]
    elif "/raw/upload/" in url:
        resource_type = "raw"
        suffix = url.split("/raw/upload/", 1)[1]
    else:
        return None

    if suffix.startswith("v") and "/" in suffix:
        suffix = suffix.split("/", 1)[1]

    filename = suffix.rsplit("/", 1)[-1]
    if "." in filename:
        suffix = suffix.rsplit(".", 1)[0]

    return suffix, resource_type


def _delete_from_cloudinary(url: str) -> None:
    settings = get_settings()
    if not settings.cloudinary_is_configured():
        return

    target = _cloudinary_target_from_url(url)
    if target is None:
        return

    public_id, resource_type = target
    _configure_cloudinary()
    cloudinary.uploader.destroy(public_id, resource_type=resource_type)


async def save_image_upload(
    file: UploadFile,
    *,
    owner_id: uuid.UUID,
    category: str,
    max_bytes: int,
) -> str:
    if file.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image must be JPEG, PNG, or WebP",
        )

    content = await file.read()
    _validate_size(content, max_bytes, "Image")

    settings = get_settings()
    if settings.cloudinary_is_configured():
        return await _upload_bytes_to_cloudinary_async(
            content,
            folder=_cloudinary_folder(category, owner_id),
            resource_type="image",
        )

    extension = ALLOWED_IMAGE_CONTENT_TYPES[file.content_type]
    filename = f"{uuid.uuid4()}{extension}"
    relative = f"{category}/{owner_id}/{filename}"
    destination = get_upload_root() / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return build_public_url(relative)


async def save_resume_upload(
    file: UploadFile,
    *,
    owner_id: uuid.UUID,
) -> str:
    settings = get_settings()
    if file.content_type not in ALLOWED_RESUME_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume must be a PDF file",
        )

    content = await file.read()
    _validate_size(content, settings.MAX_RESUME_SIZE_BYTES, "Resume")

    if settings.cloudinary_is_configured():
        return await _upload_bytes_to_cloudinary_async(
            content,
            folder=_cloudinary_folder("freelancers/resume", owner_id),
            resource_type="raw",
        )

    extension = ALLOWED_RESUME_CONTENT_TYPES[file.content_type]
    filename = f"{uuid.uuid4()}{extension}"
    relative = f"freelancers/{owner_id}/resume/{filename}"
    destination = get_upload_root() / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return build_public_url(relative)


def delete_upload_if_local(url: str | None) -> None:
    if not url:
        return

    if url.startswith("/uploads/"):
        relative = url.removeprefix("/uploads/")
        path = get_upload_root() / relative
        if path.is_file():
            path.unlink()
        return

    if "res.cloudinary.com" in url:
        try:
            _delete_from_cloudinary(url)
        except Exception:
            return
