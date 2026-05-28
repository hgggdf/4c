"""用户文档上传入库路由。

支持 PDF / Word (.docx) / TXT / Excel (.xlsx/.xls)。
文本提取后写入知识库：
- 携带 session_id 的上传写入私有 collection（report_private），仅该 session 可检索
- 不携带 session_id 的上传写入公有 report collection（向后兼容）
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

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
async def upload_doc(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
):
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

    # doc_id incorporates session_id so different users' same-named files don't collide
    id_seed = f"{session_id or 'public'}:{file.filename}:{len(data)}"
    doc_id = hashlib.md5(id_seed.encode()).hexdigest()[:16]

    is_private = bool(session_id)
    metadata = {
        "doc_type": "report_private" if is_private else "report",
        "doc_id": doc_id,
        "title": Path(file.filename or "").stem,
        "source_type": "user_upload",
        "source_table": "user_upload",
        "source_pk": doc_id,
        "is_hot": 1,
        "uploader_id": session_id or "",
        "is_private": 1 if is_private else 0,
    }

    # Determine target collection
    doc_type = "report_private" if is_private else "report"

    chunks_written = 0

    # Write to vector store
    try:
        from app.knowledge.store import get_vector_store
        vs = get_vector_store()
        chunks_written = vs.add_document(
            text,
            doc_type=doc_type,
            metadata=metadata,
            doc_id=doc_id,
        )
    except Exception as vec_exc:
        logger.debug("向量库写入跳过（%s），降级到 TF-IDF", vec_exc)

    # TF-IDF fallback — metadata already carries uploader_id / is_private for filter
    if chunks_written == 0:
        try:
            from app.knowledge.store import chunk_text, get_store
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
        pass

    visibility = "私有（仅当前会话可用）" if is_private else "公有"
    return {
        "success": True,
        "file_name": file.filename,
        "doc_id": doc_id,
        "chars": len(text),
        "chunks": chunks_written,
        "is_private": is_private,
        "message": f"文档已入库（{visibility}），共 {chunks_written} 个片段，可在对话中直接引用",
    }
