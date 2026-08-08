from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.config import INSTANCE_DIR
from app.core.logger import get_logger
from app.domain.ports.moments_port import MomentsRepository

logger = get_logger(__name__)

_IMAGE_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".bmp",
        ".jfif",
        ".jpe",
        ".svg",
        ".tif",
        ".tiff",
        ".avif",
        ".heic",
        ".ico",
    }
)
_VIDEO_SUFFIXES = frozenset({".mp4", ".webm", ".mov", ".mkv", ".m4v"})

# Magic bytes for MIME-type verification at upload time.
# These prevent a malicious actor from uploading, say, a PHP script
# with an extension of .jpg to bypass server-side extension checks.
_MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF????WEBP",),  # struct-format: first 4 bytes = RIFF, then 4 bytes size, then WEBP
    ".pdf": (b"%PDF",),
    ".zip": (b"\x50\x4b\x03\x04",),  # DOCX/XLSX/PPTX are ZIP-based
    ".docx": (b"\x50\x4b\x03\x04",),
    ".xlsx": (b"\x50\x4b\x03\x04",),
}

# Number of bytes to read for magic-byte check (max magic length is 12 for WEBP RIFF header)
_MAGIC_READ_LEN = 12


def _verify_magic_bytes(file: FileStorage, suffix: str) -> bool:
    """Verify uploaded file content matches its declared extension.

    Reads the first few bytes of the file and compares against known magic
    byte signatures for the given file extension. This prevents MIME-bypass
    attacks where a malicious file (e.g., executable, script) is renamed with
    a trusted extension like .jpg or .png.

    Returns True if magic bytes match (or cannot be verified for unknown types).
    """
    expected_patterns = _MAGIC_BYTES.get(suffix.lower())
    if not expected_patterns:
        # Unknown extension — skip magic-byte check (extension check already applies)
        return True

    pos = file.tell() if hasattr(file, "tell") else 0
    file.seek(0)
    header = file.read(_MAGIC_READ_LEN)
    file.seek(pos)

    for pattern in expected_patterns:
        # Handle struct-format patterns (e.g., RIFF????WEBP for WEBP)
        if b"?" in pattern:
            fmt_pattern = pattern.replace(b"?", b"")
            # Extract fixed segments from the pattern
            parts = []
            offset = 0
            for i, b in enumerate(fmt_pattern):
                if b != ord("?"):
                    if not parts or parts[-1][1] != i:
                        parts.append((i, bytes([b])))
                    else:
                        parts[-1] = (parts[-1][0], parts[-1][1] + bytes([b]))
            # Reconstruct: match non-wildcard bytes at their positions
            matches = True
            for start, seg in parts:
                end = start + len(seg)
                if header[start:end] != seg:
                    matches = False
                    break
            if matches:
                return True
        else:
            if header[: len(pattern)] == pattern:
                return True

    return False


def _media_type_from_upload(*, suffix: str, mimetype: str) -> str:
    mt = (mimetype or "").lower()
    if mt.startswith("image/"):
        return "image"
    if mt.startswith("video/"):
        return "video"
    s = suffix.lower()
    if s in _VIDEO_SUFFIXES:
        return "video"
    if s in _IMAGE_SUFFIXES:
        return "image"
    return "file"


# Maximum upload size: 10 MB
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class MomentsService:
    def __init__(self, repo: MomentsRepository) -> None:
        self._repo = repo

    def list_feed(self, *, limit: int = 50, before_post_id: int | None = None) -> GenericResponseDTO:
        items = self._repo.list_feed(limit=limit, before_post_id=before_post_id)
        next_cursor = items[-1]["post_id"] if items else None
        return {"ok": True, "items": items, "next_before_post_id": next_cursor}

    def create_post(
        self,
        *,
        actor_type: str,
        actor_id: str,
        author_name: str,
        content_text: str,
        attachments: list[dict[str, Any]] | None = None,
        content: dict[str, Any] | None = None,
        market_date: str | None = None,
    ) -> GenericResponseDTO:
        text = (content_text or "").strip()
        atts = attachments or []
        if len(atts) > 9:
            return {"ok": False, "error": "too_many_attachments"}
        if not text and not atts:
            return {"ok": False, "error": "content_empty"}
        post_id = self._repo.create_post(
            actor_type=actor_type,
            actor_id=actor_id,
            author_name=author_name,
            content_text=text,
            content=content,
            market_date=market_date,
        )
        for a in atts:
            try:
                self._repo.add_attachment(
                    post_id=post_id,
                    media_type=str(a.get("media_type") or "file"),
                    file_name=str(a.get("file_name") or ""),
                    file_path=str(a.get("file_path") or ""),
                    file_url=str(a.get("file_url") or ""),
                    mime_type=str(a.get("mime_type") or ""),
                    size_bytes=int(a.get("size_bytes") or 0),
                    meta=a.get("meta") if isinstance(a.get("meta"), dict) else None,
                )
            except Exception:
                logger.exception("add_attachment failed post_id=%s", post_id)
        return {"ok": True, "post_id": int(post_id)}

    def toggle_like(self, *, post_id: int, user_id: str) -> GenericResponseDTO:
        return self._repo.toggle_like(post_id=post_id, user_id=user_id)

    def add_comment(self, *, post_id: int, user_id: str, author_name: str, content_text: str) -> GenericResponseDTO:
        post = self._repo.get_post(post_id)
        out = self._repo.add_comment(
            post_id=post_id,
            user_id=user_id,
            author_name=author_name,
            content_text=content_text,
        )
        if post is not None:
            out["post"] = {"actor_type": post.get("actor_type"), "actor_id": post.get("actor_id")}
        return out

    def list_comments(self, *, post_id: int, limit: int = 50) -> GenericResponseDTO:
        items = self._repo.list_comments(post_id=post_id, limit=limit)
        return {"ok": True, "items": items, "count": len(items)}

    def delete_user_post(self, *, post_id: int, user_keys: set[str]) -> GenericResponseDTO:
        post = self._repo.get_post(post_id)
        if post is None:
            return {"ok": False, "error": "not_found"}
        if str(post.get("actor_type") or "") != "user":
            return {"ok": False, "error": "forbidden"}
        if str(post.get("actor_id") or "") not in user_keys:
            return {"ok": False, "error": "forbidden"}
        if not self._repo.delete_post(int(post_id)):
            return {"ok": False, "error": "not_found"}
        return {"ok": True}

    def update_user_post(
        self,
        *,
        post_id: int,
        user_keys: set[str],
        content_text: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> GenericResponseDTO:
        post = self._repo.get_post(post_id)
        if post is None:
            return {"ok": False, "error": "not_found"}
        if str(post.get("actor_type") or "") != "user":
            return {"ok": False, "error": "forbidden"}
        if str(post.get("actor_id") or "") not in user_keys:
            return {"ok": False, "error": "forbidden"}
        text = (content_text or "").strip()
        atts = attachments if attachments is not None else None
        if atts is not None:
            if len(atts) > 9:
                return {"ok": False, "error": "too_many_attachments"}
            if not text and not atts:
                return {"ok": False, "error": "content_empty"}
            self._repo.delete_attachments_for_post(int(post_id))
            for a in atts:
                try:
                    self._repo.add_attachment(
                        post_id=int(post_id),
                        media_type=str(a.get("media_type") or "file"),
                        file_name=str(a.get("file_name") or ""),
                        file_path=str(a.get("file_path") or ""),
                        file_url=str(a.get("file_url") or ""),
                        mime_type=str(a.get("mime_type") or ""),
                        size_bytes=int(a.get("size_bytes") or 0),
                        meta=a.get("meta") if isinstance(a.get("meta"), dict) else None,
                    )
                except Exception:
                    logger.exception("update_user_post add_attachment failed post_id=%s", post_id)
        else:
            keep_n = self._repo.count_attachments_for_post(int(post_id))
            if not text and keep_n == 0:
                return {"ok": False, "error": "content_empty"}
        if not self._repo.update_post(int(post_id), content_text=text):
            return {"ok": False, "error": "not_found"}
        return {"ok": True, "post_id": int(post_id)}

    def save_upload(self, file: FileStorage) -> GenericResponseDTO:
        if not file or not getattr(file, "filename", ""):
            return {"ok": False, "error": "file_required"}

        # Enforce file size cap BEFORE reading or saving
        file.seek(0, 2)  # seek to end
        size = file.tell()
        file.seek(0)  # rewind
        if size > _MAX_UPLOAD_BYTES:
            logger.warning("Upload rejected: size %d exceeds max %d for %s", size, _MAX_UPLOAD_BYTES, secure_filename(str(file.filename or "")))
            return {"ok": False, "error": "file_too_large", "meta": {"max_bytes": _MAX_UPLOAD_BYTES}}
        orig = str(file.filename or "")
        safe = secure_filename(orig) or "upload.bin"
        suffix = Path(safe).suffix.lower()
        mimetype = str(getattr(file, "mimetype", "") or "")
        media_type = _media_type_from_upload(suffix=suffix, mimetype=mimetype)

        # Security: verify file content matches declared extension via magic bytes.
        # Prevents MIME-bypass attacks where a malicious file is renamed with a
        # trusted extension (e.g., uploading a script as .png).
        if not _verify_magic_bytes(file, suffix):
            logger.warning("Magic bytes mismatch for upload: filename=%s suffix=%s", orig, suffix)
            return {"ok": False, "error": "file_type_mismatch"}
        # 兼容移动端/剪贴板上传：部分浏览器可能不带扩展名，导致 /uploads 返回的 mimetype 不易被桌面端渲染。
        # 这里按 mimetype 为落盘文件补齐扩展名，使 img/video 在 PC 上也能稳定显示。
        mt = mimetype.lower()
        if media_type == "image" and suffix not in _IMAGE_SUFFIXES:
            if "png" in mt:
                suffix = ".png"
            elif "gif" in mt:
                suffix = ".gif"
            elif "webp" in mt:
                suffix = ".webp"
            elif "svg" in mt:
                suffix = ".svg"
            elif "avif" in mt:
                suffix = ".avif"
            else:
                suffix = ".jpg"
        if media_type == "video" and suffix not in _VIDEO_SUFFIXES:
            if "webm" in mt:
                suffix = ".webm"
            else:
                suffix = ".mp4"
        # 物理路径：instance/uploads/moments/<file>
        # 公开 URL：/uploads/moments/<file>（不要再拼一层 uploads，否则会成 /uploads/uploads/...）
        rel_dir = Path("moments")
        out_dir = (INSTANCE_DIR / "uploads" / rel_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        key = uuid4().hex
        out_name = f"{key}{suffix}"
        out_path = out_dir / out_name
        file.save(str(out_path))
        size = out_path.stat().st_size if out_path.exists() else 0
        rel_path = (rel_dir / out_name).as_posix()
        url = f"/uploads/{rel_path}"
        return {
            "ok": True,
            "media_type": media_type,
            "file_name": safe,
            "file_path": rel_path,
            "file_url": url,
            "mime_type": mimetype,
            "size_bytes": int(size),
            "meta": {},
        }

