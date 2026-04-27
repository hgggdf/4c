"""文档转图片服务：从本地文件或 source_url 获取研报/公告/新闻，转为 base64 图片。"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import textwrap
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_FILES_ROOT = _BASE_DIR / "data" / "processed" / "today"

RESEARCH_REPORT_DIR = _FILES_ROOT / "research_report" / "files"
ANNOUNCEMENT_DIR    = _FILES_ROOT / "announcement" / "files"
NEWS_DIR            = _FILES_ROOT / "news" / "files"


# ── 文件查找 ──────────────────────────────────────────────────────────────────

def find_research_report(stock_code: str, publish_date: str) -> Optional[Path]:
    date_str = publish_date.replace("-", "") if publish_date else ""
    if not stock_code or not date_str:
        return None
    target = RESEARCH_REPORT_DIR / f"company_{stock_code}_{date_str}.pdf"
    if target.exists():
        return target
    for f in RESEARCH_REPORT_DIR.glob(f"company_{stock_code}_{date_str}*.pdf"):
        return f
    return None


def find_industry_report(industry_code: str, publish_date: str) -> Optional[Path]:
    date_str = publish_date.replace("-", "") if publish_date else ""
    if industry_code and date_str:
        target = RESEARCH_REPORT_DIR / f"industry_{industry_code}_{date_str}.pdf"
        if target.exists():
            return target
        for f in RESEARCH_REPORT_DIR.glob(f"industry_{industry_code}_{date_str}*.pdf"):
            return f
    # 没有精确匹配时返回 None，让调用方 fallback 到 source_url
    return None


def find_announcement(stock_code: str, publish_date: str) -> Optional[Path]:
    date_str = publish_date.replace("-", "") if publish_date else ""
    if not stock_code or not date_str:
        return None
    for f in ANNOUNCEMENT_DIR.glob(f"{stock_code}_{date_str}*.pdf"):
        return f
    return None


def find_news(news_uid: str) -> Optional[Path]:
    if not news_uid:
        return None
    target = NEWS_DIR / f"news_{news_uid}.html"
    return target if target.exists() else None


def find_doc_file(
    doc_type: str,
    stock_code: str = "",
    industry_code: str = "",
    publish_date: str = "",
    news_uid: str = "",
) -> Optional[Path]:
    if doc_type == "research_report":
        if stock_code:
            return find_research_report(stock_code, publish_date)
        return find_industry_report(industry_code, publish_date)
    elif doc_type == "announcement":
        return find_announcement(stock_code, publish_date)
    elif doc_type == "news":
        return find_news(news_uid)
    return None


# ── PDF 文字提取 ──────────────────────────────────────────────────────────────

def _clean_pdf_text(text: str) -> str:
    """清洗 PDF 提取的文字，过滤噪音行，保留可读段落。"""
    lines = text.splitlines()
    clean = []
    for line in lines:
        line = line.strip()
        if not line:
            clean.append("")
            continue

        # 过滤 [Table_xxx] PDF 内部标记
        if re.match(r'^\[T\w*a\w*b\w*l\w*e\w*_', line):
            continue

        # 过滤纯数字/百分比行
        if re.match(r'^-?\d+(\.\d+)?%?$', line):
            continue

        # 过滤日期序列行（如 "2025-04 2025-07 ..."）
        if re.match(r'^(\d{4}-\d{2}\s+){2,}', line):
            continue

        # 过滤纯数字组合行（如 "1,600 51.00"）
        if re.match(r'^[\d,\.\s]+$', line):
            continue

        # 过滤没有中文的短行（图表残留）
        chinese_count = sum(1 for c in line if '一' <= c <= '鿿')
        if chinese_count == 0 and len(line) <= 30:
            continue

        # 过滤中文极少的短行（如 "39% 13.63%。" 这种图表Y轴混入正文）
        if len(line) <= 15 and chinese_count <= 2:
            continue

        # 过滤替换字符
        if line.count('?') > len(line) * 0.3:
            continue

        # 过滤可读字符比例过低的行
        total = len(line)
        readable = sum(
            1 for c in line
            if '一' <= c <= '鿿'
            or c.isdigit()
            or (c.isascii() and c in
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
                '0123456789 .,;:!?()[]%+-/\'"')
            or c in '、。，；：！？（）《》""''·—～'
        )
        if total > 4 and readable / total < 0.5:
            continue

        # 行首是"数字% 正文"混排（图表Y轴+正文），截取正文部分
        # 匹配 "39% 13.63%。2026年..." 或 "39% 降10.36%..."
        m = re.match(r'^-?\d+%\s+(.*)', line)
        if m:
            rest = m.group(1).strip()
            # rest 可能还是 "13.63%。2026年..."，继续找第一个中文字符
            cn = re.search(r'[一-鿿]', rest)
            if cn:
                line = rest[cn.start():]
            else:
                continue  # 没有中文，整行丢弃

        # 行首是"数字 中文"混排（表格数据+正文，如 "18.40 突破，CDMO..."）
        m = re.match(r'^[\d,\.]+\s+([一-鿿].*)', line)
        if m:
            line = m.group(1)

        # 行内含"表格标签 数字 正文"（如 "最新收盘价（元） 18.40 突破，CDMO..."）
        # 过滤掉"中文标签 数字"前缀，只保留后面的正文
        m = re.match(r'^[一-鿿\w（）/]+\s+[\d,\./%]+\s+([一-鿿].*)', line)
        if m:
            line = m.group(1)

        # 行尾跟着孤立数字（如 "...增长通道。 1,400 48.00"），截掉尾部数字
        line = re.sub(r'\s+[\d,\.]+\s+[\d,\.]+\s*$', '', line).strip()
        line = re.sub(r'\s+[\d,\.]+\s*$', '', line).strip()

        # 过滤"单位说明行"（如 "人民币(元) 成交金额(百万元)"）
        if re.match(r'^[人民币元成交金额百万\(\)（）\s]+$', line):
            continue

        # 过滤"资料来源"行
        if re.match(r'^资料来源[：:]', line):
            continue

        if line:
            clean.append(line)

    # 合并连续空行为单个空行
    result = []
    prev_empty = False
    for line in clean:
        if line == "":
            if not prev_empty:
                result.append("")
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False

    return "\n".join(result).strip()


def pdf_to_text_pages(file_path: Path, max_pages: int = 3) -> list[str]:
    """PDF 提取文字，每页返回一段清洗后的文字。"""
    try:
        import pdfplumber
    except ImportError:
        return []
    results = []
    try:
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages[:max_pages]:
                words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
                if not words:
                    continue
                # 按 top 坐标分组，同一行的词拼在一起
                lines_map: dict[int, list[str]] = {}
                for w in words:
                    row = round(w["top"] / 8) * 8
                    lines_map.setdefault(row, []).append(w["text"])
                raw_lines = [" ".join(ws) for _, ws in sorted(lines_map.items())]
                text = "\n".join(raw_lines)
                cleaned = _clean_pdf_text(text)
                if cleaned:
                    results.append(cleaned)
    except Exception as exc:
        logger.warning("pdf_to_text_pages failed for %s: %s", file_path, exc)
    return results


def pdf_to_base64_images(file_path: Path, max_pages: int = 3) -> list[str]:
    """PDF 转 base64 图片列表（最多 max_pages 页）。"""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed")
        return []
    results = []
    try:
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages[:max_pages]:
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                raw_lines = text.splitlines()
                lines: list[str] = []
                for raw in raw_lines:
                    if len(raw) > 80:
                        lines.extend(textwrap.wrap(raw, width=80))
                    else:
                        lines.append(raw)
                img_bytes = _render_text_to_image(lines)
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                results.append(f"data:image/png;base64,{b64}")
    except Exception as exc:
        logger.warning("pdf_to_base64_images failed for %s: %s", file_path, exc)
    return results


def _render_text_to_image(lines: list[str], width: int = 900, font_size: int = 16) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    line_height = font_size + 6
    padding = 24
    img_height = max(400, len(lines) * line_height + padding * 2)
    img = Image.new("RGB", (width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = None
    for fp in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
               "C:/Windows/Fonts/simsun.ttc", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"]:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue
    y = padding
    for line in lines:
        draw.text((padding, y), line, fill=(30, 30, 30), font=font)
        y += line_height
        if y > img_height - padding:
            break
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ── HTML 文字提取 ─────────────────────────────────────────────────────────────

def _extract_html_text(html_content: str) -> list[str]:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        # 按优先级找正文容器，兼容东方财富 zw-content 等
        body = (
            soup.find("article")
            or soup.find("div", class_=re.compile(r"zw.content|content|article|body|text", re.I))
            or soup.find("body")
            or soup
        )
        text = body.get_text(separator="\n")
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html_content)

    lines = []
    for line in text.splitlines():
        line = line.strip().replace("　", "")  # 去掉全角空格
        if len(line) < 4:
            continue
        if len(line) > 100:
            lines.extend(textwrap.wrap(line, width=100))
        else:
            lines.append(line)
        if len(lines) >= 150:
            break
    return lines


def html_file_to_text(file_path: Path) -> str:
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = _extract_html_text(content)
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("html_file_to_text failed for %s: %s", file_path, exc)
        return ""


def url_to_text(url: str) -> str:
    try:
        import requests
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        # 东方财富等主流财经网站均为 UTF-8，强制指定避免 apparent_encoding 误判
        resp.encoding = "utf-8"
        lines = _extract_html_text(resp.text)
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("url_to_text failed for %s: %s", url, exc)
        return ""


def html_file_to_base64_image(file_path: Path) -> list[str]:
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = _extract_html_text(content)
        if not lines:
            return []
        img_bytes = _render_text_to_image(lines)
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return [f"data:image/png;base64,{b64}"]
    except Exception as exc:
        logger.warning("html_file_to_base64_image failed for %s: %s", file_path, exc)
        return []


def url_to_base64_image(url: str) -> list[str]:
    try:
        import requests
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.encoding = "utf-8"
        lines = _extract_html_text(resp.text)
        if not lines:
            return []
        img_bytes = _render_text_to_image(lines)
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return [f"data:image/png;base64,{b64}"]
    except Exception as exc:
        logger.warning("url_to_base64_image failed for %s: %s", url, exc)
        return []


# ── 统一入口 ──────────────────────────────────────────────────────────────────

def get_doc_images(
    doc_type: str,
    stock_code: str = "",
    industry_code: str = "",
    publish_date: str = "",
    news_uid: str = "",
    source_url: str = "",
    max_pages: int = 3,
) -> dict:
    local_path = find_doc_file(
        doc_type,
        stock_code=stock_code,
        industry_code=industry_code,
        publish_date=publish_date,
        news_uid=news_uid,
    )

    if local_path:
        suffix = local_path.suffix.lower()
        if suffix == ".pdf":
            text_pages = pdf_to_text_pages(local_path, max_pages=max_pages)
            images = pdf_to_base64_images(local_path, max_pages=max_pages)
        else:
            text_pages = [html_file_to_text(local_path)]
            images = html_file_to_base64_image(local_path)
        if text_pages or images:
            return {"images": images, "text_pages": text_pages, "source": "local", "file_name": local_path.name}

    if source_url:
        text = url_to_text(source_url)
        images = url_to_base64_image(source_url)
        if text or images:
            return {"images": images, "text_pages": [text] if text else [], "source": "url", "file_name": ""}

    return {"images": [], "text_pages": [], "source": "none", "file_name": ""}


__all__ = ["get_doc_images", "find_doc_file", "pdf_to_base64_images", "html_file_to_base64_image"]