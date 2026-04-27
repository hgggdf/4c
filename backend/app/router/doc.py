"""文档预览路由：返回研报/公告/新闻的 base64 图片。"""

from fastapi import APIRouter
from app.service.doc_image_service import get_doc_images

router = APIRouter(prefix="/api/doc", tags=["doc"])


@router.get("/preview")
def doc_preview(
    doc_type: str,
    stock_code: str = "",
    industry_code: str = "",
    publish_date: str = "",
    news_uid: str = "",
    source_url: str = "",
    max_pages: int = 3,
):
    """
    返回文档的 base64 图片列表。
    doc_type: research_report | announcement | news
    """
    result = get_doc_images(
        doc_type,
        stock_code=stock_code,
        industry_code=industry_code,
        publish_date=publish_date,
        news_uid=news_uid,
        source_url=source_url,
        max_pages=min(max_pages, 5),
    )
    return result
