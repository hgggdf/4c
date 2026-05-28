"""用户文档上传入库路由。

支持 PDF / Word (.docx) / TXT / Excel (.xlsx/.xls)。
文本提取后写入 TF-IDF 兜底知识库，如 Chroma 可用则同时写向量库。
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".xlsx", ".xls"}
MAX_SIZE_MB = 20


def _extract_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        for enc in ("utf-8", "gbk", "utf-16"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    if suffix == ".pdf":
        import io
        import pdfplumber
        text_parts: list[str] = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)

    if suffix == ".docx":
        import io
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if suffix in (".xlsx", ".xls"):
        import io
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows: list[str] = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None and str(c).strip()]
                if cells:
                    rows.append("\t".join(cells))
        return "\n".join(rows)

    return ""


@router.post("/upload_doc")
async def upload_doc(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {suffix}，支持：PDF、Word、TXT、Excel",
        )

    data = await file.read()
    if len(data) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"文件超过 {MAX_SIZE_MB}MB 限制")

    try:
        text = _extract_text(file.filename or "", data)
    except Exception as exc:
        logger.warning("文档解析失败 %s: %s", file.filename, exc)
        raise HTTPException(status_code=422, detail=f"文档解析失败：{exc}") from exc

    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="文档内容为空，无法入库")

    doc_id = hashlib.md5(f"{file.filename}:{len(data)}".encode()).hexdigest()[:16]
    metadata = {
        "doc_type": "report",
        "doc_id": doc_id,
        "title": Path(file.filename or "").stem,
        "source_type": "user_upload",
        "source_table": "user_upload",
        "source_pk": doc_id,
        "is_hot": 1,
    }

    chunks_written = 0

    # 优先写向量库，失败降级到 TF-IDF
    try:
        from app.knowledge.store import get_vector_store
        vs = get_vector_store()
        chunks_written = vs.add_document(text, doc_type="report", metadata=metadata, doc_id=doc_id)
    except Exception as vec_exc:
        logger.debug("向量库写入跳过（%s），降级到 TF-IDF", vec_exc)

    if chunks_written == 0:
        try:
            from app.knowledge.store import get_store, chunk_text
            store = get_store()
            for chunk in chunk_text(text):
                store.docs.append({"text": chunk, "meta": metadata})
            store._rebuild_index()
            store._save()
            chunks_written = len(chunk_text(text))
        except Exception as tfidf_exc:
            logger.error("TF-IDF 写入失败: %s", tfidf_exc)
            raise HTTPException(status_code=500, detail="文档入库失败，请稍后重试") from tfidf_exc

    # Kick off rNPV parameter extraction in the background (non-blocking)
    try:
        from agent.integration.rnpv_extractor import extract_rnpv_params_async
        extract_rnpv_params_async(doc_id, text)
    except Exception:
        pass  # extraction is best-effort; never block the upload response

    return {
        "success": True,
        "file_name": file.filename,
        "doc_id": doc_id,
        "chars": len(text),
        "chunks": chunks_written,
        "message": f"文档已入库，共 {chunks_written} 个片段，可在对话中直接引用",
    }
