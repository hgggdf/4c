"""公告事件查询工具函数"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer
from app.service.requests import StockCodeDaysRequest


def get_raw_announcements(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取原始公告数据

    Args:
        stock_code: 股票代码
        days: 查询最近N天的公告，默认365天

    Returns:
        原始公告列表，每条包含：
        - id: 公告ID
        - stock_code: 股票代码
        - title: 公告标题
        - publish_date: 发布日期
        - announcement_type: 公告类型
        - exchange: 交易所
        - content: 公告内容
        - source_url: 来源URL
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_raw_announcements(req)
    if not result.success:
        raise ValueError(f"获取原始公告失败: {result.message}")
    return result.data


def get_structured_announcements(
    stock_code: str, days: int = 365, category: str | None = None
) -> list[dict[str, Any]]:
    """
    获取结构化公告数据

    Args:
        stock_code: 股票代码
        days: 查询最近N天的公告，默认365天
        category: 公告分类过滤，可选

    Returns:
        结构化公告列表，每条包含：
        - id: 结构化公告ID
        - announcement_id: 原始公告ID
        - stock_code: 股票代码
        - category: 分类（研发进展/财务业绩/监管处罚等）
        - summary_text: 摘要文本
        - key_fields_json: 关键字段JSON
        - signal_type: 信号类型（opportunity/risk/neutral）
        - risk_level: 风险等级
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days, category=category)
    result = container.announcement.get_structured_announcements(req)
    if not result.success:
        raise ValueError(f"获取结构化公告失败: {result.message}")
    return result.data


def get_drug_approvals(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取药品批准事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        药品批准事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - drug_name: 药品名称
        - approval_type: 批准类型（上市批准/临床批准等）
        - approval_date: 批准日期
        - indication: 适应症
        - drug_stage: 药品阶段
        - is_innovative_drug: 是否创新药
        - review_status: 审评状态
        - market_scope: 市场范围
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_drug_approvals(req)
    if not result.success:
        raise ValueError(f"获取药品批准事件失败: {result.message}")
    return result.data


def get_clinical_trials(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取临床试验事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        临床试验事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - drug_name: 药品名称
        - trial_phase: 试验阶段（I期/II期/III期）
        - event_type: 事件类型（启动/完成/中止等）
        - event_date: 事件日期
        - indication: 适应症
        - summary_text: 摘要文本
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_clinical_trials(req)
    if not result.success:
        raise ValueError(f"获取临床试验事件失败: {result.message}")
    return result.data


def get_procurement_events(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取集采中标事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        集采中标事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - drug_name: 药品名称
        - procurement_round: 集采轮次
        - bid_result: 中标结果
        - price_change_ratio: 价格变化比例
        - event_date: 事件日期
        - impact_summary: 影响摘要
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_procurement_events(req)
    if not result.success:
        raise ValueError(f"获取集采中标事件失败: {result.message}")
    return result.data


def get_regulatory_risks(stock_code: str, days: int = 365) -> list[dict[str, Any]]:
    """
    获取监管风险事件

    Args:
        stock_code: 股票代码
        days: 查询最近N天的事件，默认365天

    Returns:
        监管风险事件列表，每条包含：
        - id: 事件ID
        - stock_code: 股票代码
        - risk_type: 风险类型（处罚/警告/调查等）
        - event_date: 事件日期
        - risk_level: 风险等级
        - summary_text: 摘要文本
    """
    container = ServiceContainer.build_default()
    req = StockCodeDaysRequest(stock_code=stock_code, days=days)
    result = container.announcement.get_regulatory_risks(req)
    if not result.success:
        raise ValueError(f"获取监管风险事件失败: {result.message}")
    return result.data


def get_company_event_summary(stock_code: str, days: int = 365) -> dict[str, Any]:
    """
    获取公司事件汇总。从 announcement_hot 表读取原始公告，按关键词分类为
    机会类/风险类/中性，并识别药品批准、临床试验、集采等子类型。
    """
    from datetime import datetime, timedelta
    from app.core.database.session import SessionLocal
    from sqlalchemy import text

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT title, publish_date, announcement_type, source_url
            FROM announcement_hot
            WHERE stock_code = :code AND publish_date >= :cutoff
            ORDER BY publish_date DESC
            LIMIT 500
        """), {"code": stock_code, "cutoff": cutoff}).fetchall()

    _OPP = ["获批", "批准", "上市", "中标", "新药", "创新药", "临床", "合作",
            "授权", "许可", "收购", "并购", "增持", "回购", "分红", "业绩增长",
            "扩产", "研发进展", "III期", "II期"]
    _RISK = ["处罚", "警告", "调查", "违规", "诉讼", "仲裁", "集采降价", "降价",
             "撤回", "暂停", "中止", "失败", "亏损", "减持", "质押", "监管",
             "问询", "立案", "行政处罚"]
    _APPROVAL = ["获批", "批准", "上市许可", "新药申请", "注册申请"]
    _CLINICAL = ["临床", "I期", "II期", "III期", "试验", "适应症"]
    _PROCURE = ["集采", "带量采购", "中标", "采购", "招标"]

    def classify(title):
        for kw in _RISK:
            if kw in title:
                return "risk"
        for kw in _OPP:
            if kw in title:
                return "opportunity"
        return "neutral"

    def subtype(title):
        for kw in _APPROVAL:
            if kw in title:
                return "drug_approval"
        for kw in _CLINICAL:
            if kw in title:
                return "clinical_trial"
        for kw in _PROCURE:
            if kw in title:
                return "procurement"
        return "general"

    opportunity_items, risk_items, neutral_items = [], [], []
    drug_approvals, clinical_trials, procurement_events = [], [], []
    counts: dict[str, int] = {}

    for row in rows:
        title = str(row[0] or "")
        date = str(row[1] or "")[:10]
        ann_type = str(row[2] or "")
        url = str(row[3] or "")

        sig = classify(title)
        sub = subtype(title)
        entry = {"title": title, "date": date, "announcement_type": ann_type,
                 "source_url": url, "signal_type": sig, "subtype": sub}

        if sig == "opportunity":
            opportunity_items.append(entry)
        elif sig == "risk":
            risk_items.append(entry)
        else:
            neutral_items.append(entry)

        if sub == "drug_approval":
            drug_approvals.append(entry)
        elif sub == "clinical_trial":
            clinical_trials.append(entry)
        elif sub == "procurement":
            procurement_events.append(entry)

        counts[ann_type] = counts.get(ann_type, 0) + 1

    return {
        "stock_code": stock_code,
        "days": days,
        "total_announcements": len(rows),
        "data_source": "announcement_hot（关键词分类）",
        "structured_announcements": (opportunity_items + risk_items)[:20],
        "drug_approvals": drug_approvals[:10],
        "clinical_trials": clinical_trials[:10],
        "procurement_events": procurement_events[:10],
        "regulatory_risks": risk_items[:10],
        "opportunity_items": opportunity_items[:15],
        "risk_items": risk_items[:15],
        "neutral_items": neutral_items[:10],
        "counts_by_category": counts,
    }


__all__ = [
    "get_raw_announcements",
    "get_structured_announcements",
    "get_drug_approvals",
    "get_clinical_trials",
    "get_procurement_events",
    "get_regulatory_risks",
    "get_company_event_summary",
]
