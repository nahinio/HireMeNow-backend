import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.services.uploads import (
    build_public_url,
    delete_upload_if_local,
    save_image_upload,
    save_resume_upload,
)


class MockUploadFile:
    def __init__(self, content: bytes, content_type: str):
        self.content_type = content_type
        self._content = content

    async def read(self) -> bytes:
        return self._content


@pytest.mark.asyncio
async def test_save_image_upload_returns_public_url(tmp_path):
    file = MockUploadFile(b"fake-image", "image/png")
    owner_id = uuid.uuid4()

    with (
        patch("app.services.uploads.get_settings") as mock_settings,
        patch("app.services.uploads.get_upload_root", return_value=tmp_path),
    ):
        mock_settings.return_value.cloudinary_is_configured.return_value = False
        url = await save_image_upload(
            file,
            owner_id=owner_id,
            category="freelancers/profile-picture",
            max_bytes=1024,
        )

    assert url.startswith("/uploads/freelancers/profile-picture/")
    assert url.endswith(".png")
    saved_files = list(tmp_path.rglob("*.png"))
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == b"fake-image"


@pytest.mark.asyncio
async def test_save_image_upload_uses_cloudinary_when_configured():
    file = MockUploadFile(b"fake-image", "image/jpeg")
    owner_id = uuid.uuid4()

    with (
        patch("app.services.uploads.get_settings") as mock_settings,
        patch(
            "app.services.uploads._upload_bytes_to_cloudinary_async",
            return_value="https://res.cloudinary.com/demo/image/upload/v1/test.jpg",
        ) as mock_upload,
    ):
        mock_settings.return_value.cloudinary_is_configured.return_value = True
        mock_settings.return_value.CLOUDINARY_FOLDER = "hiremenow"
        url = await save_image_upload(
            file,
            owner_id=owner_id,
            category="jobs/thumbnails",
            max_bytes=1024,
        )

    assert url.startswith("https://res.cloudinary.com/")
    mock_upload.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_image_upload_rejects_invalid_type():
    file = MockUploadFile(b"data", "text/plain")
    with pytest.raises(HTTPException) as exc:
        await save_image_upload(
            file,
            owner_id=uuid.uuid4(),
            category="test",
            max_bytes=1024,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_save_resume_upload_accepts_pdf(tmp_path):
    file = MockUploadFile(b"%PDF-1.4", "application/pdf")
    owner_id = uuid.uuid4()

    with (
        patch("app.services.uploads.get_settings") as mock_settings,
        patch("app.services.uploads.get_upload_root", return_value=tmp_path),
    ):
        mock_settings.return_value.cloudinary_is_configured.return_value = False
        mock_settings.return_value.MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024
        url = await save_resume_upload(file, owner_id=owner_id)

    assert url.startswith("/uploads/freelancers/")
    assert url.endswith(".pdf")


@pytest.mark.asyncio
async def test_save_resume_upload_uses_cloudinary_raw_when_configured():
    file = MockUploadFile(b"%PDF-1.4", "application/pdf")
    owner_id = uuid.uuid4()

    with (
        patch("app.services.uploads.get_settings") as mock_settings,
        patch(
            "app.services.uploads._upload_bytes_to_cloudinary_async",
            return_value="https://res.cloudinary.com/demo/raw/upload/v1/resume.pdf",
        ) as mock_upload,
    ):
        mock_settings.return_value.cloudinary_is_configured.return_value = True
        mock_settings.return_value.CLOUDINARY_FOLDER = "hiremenow"
        mock_settings.return_value.MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024
        url = await save_resume_upload(file, owner_id=owner_id)

    assert url.startswith("https://res.cloudinary.com/")
    mock_upload.assert_awaited_once()
    assert mock_upload.await_args.kwargs["resource_type"] == "raw"


@pytest.mark.asyncio
async def test_save_resume_upload_accepts_octet_stream_pdf(tmp_path):
    file = MockUploadFile(b"%PDF-1.4", "application/octet-stream")
    file.filename = "resume.pdf"
    owner_id = uuid.uuid4()

    with (
        patch("app.services.uploads.get_settings") as mock_settings,
        patch("app.services.uploads.get_upload_root", return_value=tmp_path),
    ):
        mock_settings.return_value.cloudinary_is_configured.return_value = False
        mock_settings.return_value.MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024
        url = await save_resume_upload(file, owner_id=owner_id)

    assert url.endswith(".pdf")


@pytest.mark.asyncio
async def test_save_resume_upload_rejects_non_pdf():
    file = MockUploadFile(b"not pdf", "image/png")
    with pytest.raises(HTTPException) as exc:
        await save_resume_upload(file, owner_id=uuid.uuid4())
    assert exc.value.status_code == 422


def test_delete_upload_if_local_only_removes_managed_files(tmp_path):
    relative = "freelancers/test/profile.png"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"x")

    with patch("app.services.uploads.get_upload_root", return_value=tmp_path):
        delete_upload_if_local(build_public_url(relative))
        delete_upload_if_local("https://cdn.example.com/a.png")

    assert not path.exists()


def test_delete_upload_if_local_removes_cloudinary_asset():
    url = "https://res.cloudinary.com/demo/image/upload/v1/hiremenow/test/file"

    with (
        patch("app.services.uploads.get_settings") as mock_settings,
        patch("app.services.uploads._delete_from_cloudinary") as mock_delete,
    ):
        mock_settings.return_value.cloudinary_is_configured.return_value = True
        delete_upload_if_local(url)

    mock_delete.assert_called_once_with(url)
