"""크롬 확장 다운로드 라우트 — chrome-extension/ 디렉토리를 ZIP으로 패키징해 제공."""
import io
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/extension", tags=["extension"])

# chrome-extension/ 위치 — 로컬 모노레포(루트)와 Docker(/app) 레이아웃 모두 지원
_EXT_CANDIDATES = [
    Path(__file__).parent.parent.parent.parent / "chrome-extension",  # 로컬: <repo>/chrome-extension
    Path(__file__).parent.parent.parent / "chrome-extension",         # Docker: /app/chrome-extension
]
_EXT_DIR = next((p for p in _EXT_CANDIDATES if p.exists()), _EXT_CANDIDATES[0])


@router.get("/download")
def download_extension():
    """chrome-extension/ 폴더 전체를 ZIP으로 다운로드."""
    if not _EXT_DIR.exists():
        raise HTTPException(status_code=404, detail="확장 파일을 찾을 수 없습니다")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(_EXT_DIR):
            # 숨김 폴더/캐시 제외
            if "/." in root or "__pycache__" in root or "node_modules" in root:
                continue
            for f in files:
                if f.startswith("."):
                    continue
                full = Path(root) / f
                arcname = "outreach-extension/" + str(full.relative_to(_EXT_DIR))
                zf.write(full, arcname)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="outreach-extension.zip"'},
    )
