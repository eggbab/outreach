"""크롬 확장 다운로드 라우트 — chrome-extension/ 디렉토리를 ZIP으로 패키징해 제공.

다운로드 시 서버의 BASE_URL을 manifest.json(host_permissions)과 popup.html(기본 서버주소)에
자동 주입한다. 사용자는 다운로드만 하면 자기 도메인이 박힌 확장을 받으므로,
manifest를 수동으로 편집할 필요가 없다.
"""
import io
import json
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings

router = APIRouter(prefix="/api/extension", tags=["extension"])

_EXT_CANDIDATES = [
    Path(__file__).parent.parent.parent.parent / "chrome-extension",  # 로컬: <repo>/chrome-extension
    Path(__file__).parent.parent.parent / "chrome-extension",         # Docker: /app/chrome-extension
]
_EXT_DIR = next((p for p in _EXT_CANDIDATES if p.exists()), _EXT_CANDIDATES[0])


def _server_origin() -> str | None:
    """BASE_URL에서 스킴+호스트 origin 추출 (예: https://api.example.com)."""
    base = (settings.BASE_URL or "").strip().rstrip("/")
    if not base:
        return None
    parsed = urlparse(base)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _patch_manifest(raw: bytes, origin: str) -> bytes:
    """host_permissions에 서버 origin을 추가 (localhost는 개발용으로 유지)."""
    try:
        data = json.loads(raw)
    except Exception:
        return raw
    hosts = data.get("host_permissions", [])
    pattern = f"{origin}/*"
    # 예시 도메인(*.outreach.app)은 제거하고 실제 origin으로 대체
    hosts = [h for h in hosts if "outreach.app" not in h]
    if pattern not in hosts:
        hosts.append(pattern)
    data["host_permissions"] = hosts
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def _patch_popup(raw: bytes, origin: str) -> bytes:
    """popup.html의 기본 server-url 값을 서버 origin으로 치환."""
    text = raw.decode("utf-8", errors="ignore")
    text = re.sub(
        r'(id="server-url"[^>]*value=")[^"]*(")',
        rf'\g<1>{origin}\g<2>',
        text,
    )
    text = text.replace('placeholder="http://localhost:8000"', f'placeholder="{origin}"')
    return text.encode("utf-8")


@router.get("/download")
def download_extension():
    """chrome-extension/ 폴더를 ZIP으로 다운로드 (서버 도메인 자동 주입)."""
    if not _EXT_DIR.exists():
        raise HTTPException(status_code=404, detail="확장 파일을 찾을 수 없습니다")

    origin = _server_origin()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(_EXT_DIR):
            if "/." in root or "__pycache__" in root or "node_modules" in root:
                continue
            for f in files:
                if f.startswith("."):
                    continue
                full = Path(root) / f
                rel = str(full.relative_to(_EXT_DIR))
                content = full.read_bytes()
                # 프로덕션 도메인이 설정돼 있으면 주입 (localhost 개발환경이면 원본 유지)
                if origin and "localhost" not in origin:
                    if rel == "manifest.json":
                        content = _patch_manifest(content, origin)
                    elif rel.endswith("popup.html"):
                        content = _patch_popup(content, origin)
                zf.writestr("outreach-extension/" + rel, content)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="outreach-extension.zip"'},
    )
