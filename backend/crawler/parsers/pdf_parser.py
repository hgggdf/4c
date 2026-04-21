"""
PDF 解析工具：从上交所/深交所下载年报 PDF 并提取关键财务数据
"""
from __future__ import annotations

import io
import re
import requests
import pdfplumber


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def extract_text_from_pdf_url(url: str, max_pages: int = 20) -> str:
    """下载 PDF 并提取前 max_pages 页文本"""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return extract_text_from_pdf_bytes(resp.content, max_pages)


def extract_text_from_pdf_bytes(data: bytes, max_pages: int = 20) -> str:
    """从 PDF 字节流提取文本"""
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages[:max_pages]:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)


def extract_financial_highlights(text: str) -> dict:
    """从年报文本中提取关键财务指标"""
    result: dict[str, str] = {}

    patterns = {
        "营业收入": r"营业(?:总)?收入[^\d]*?([\d,，.]+)\s*(?:万元|亿元|元)",
        "净利润": r"(?:归属.*?)?净利润[^\d]*?([\d,，.]+)\s*(?:万元|亿元|元)",
        "毛利率": r"毛利率[^\d]*?([\d.]+)\s*%",
        "ROE": r"(?:加权平均)?净资产收益率[^\d]*?([\d.]+)\s*%",
        "研发费用": r"研发(?:费用|投入)[^\d]*?([\d,，.]+)\s*(?:万元|亿元|元)",
        "研发费用率": r"研发费用率[^\d]*?([\d.]+)\s*%",
        "每股收益": r"基本每股收益[^\d]*?([\d.]+)\s*元",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            result[key] = match.group(1)

    return result


def summarize_annual_report(text: str, max_chars: int = 3000) -> str:
    """截取年报关键段落用于 AI 分析"""
    keywords = ["主要财务数据", "经营情况讨论", "核心竞争力", "研发投入", "风险因素", "业务概要"]
    segments: list[str] = []

    for kw in keywords:
        idx = text.find(kw)
        if idx != -1:
            segments.append(text[idx: idx + 500])

    if segments:
        combined = "\n\n".join(segments)
        return combined[:max_chars]

    return text[:max_chars]
