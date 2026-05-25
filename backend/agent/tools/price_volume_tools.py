"""量价分析工具函数

提供日行情序列获取、MA/量价相关/信号检测、量价异动与事件关联三个层次的分析。
数据来源：financial_hot 表中 report_type='daily' 的记录。
不依赖 numpy / pandas，全部用纯 Python 计算。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from app.core.database.session import SessionLocal
from app.service.container import ServiceContainer


# ── 内部辅助 ──────────────────────────────────────────────────────────────────

def _ma(values: list[float], n: int) -> list[float | None]:
    """计算 N 日移动均线，长度与 values 相同，前 n-1 个位置为 None。"""
    result: list[float | None] = []
    for i in range(len(values)):
        if i < n - 1:
            result.append(None)
        else:
            result.append(round(sum(values[i - n + 1: i + 1]) / n, 4))
    return result


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """计算 Pearson 相关系数，xs/ys 长度相同。"""
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return round(num / (dx * dy), 4)


def _momentum(closes: list[float], n: int) -> float | None:
    """近 n 日价格动量（累计涨跌幅）。"""
    if len(closes) < n + 1:
        return None
    start = closes[-(n + 1)]
    end = closes[-1]
    if start == 0:
        return None
    return round((end - start) / start, 4)


def _parse_target_trade_date(value: str | None, *, default_year: int) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", text)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    match = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if match:
        return date(default_year, int(match.group(1)), int(match.group(2)))
    match = re.search(r"(?<!\d)(\d{1,2})[-/](\d{1,2})(?!\d)", text)
    if match:
        return date(default_year, int(match.group(1)), int(match.group(2)))
    return None


def _row_day(row) -> date | None:
    return row.trade_date or row.report_date


def _row_payload(row) -> dict[str, Any]:
    return {
        "date": str(_row_day(row)),
        "open": float(row.open_price) if row.open_price is not None else None,
        "close": float(row.close_price) if row.close_price is not None else None,
        "high": float(row.high_price) if row.high_price is not None else None,
        "low": float(row.low_price) if row.low_price is not None else None,
        "volume": float(row.volume) if row.volume is not None else None,
        "amount": float(row.amount) if row.amount is not None else None,
        "change_pct": _change_pct_to_percent(row.change_pct),
    }


def _change_pct_to_percent(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value) * 100, 6)


def _corr_interpretation(r: float | None) -> str:
    if r is None:
        return "数据不足，无法计算"
    if r > 0.6:
        return f"量价正相关（r={r:.2f}），上涨伴随放量，趋势较为健康"
    if r > 0.3:
        return f"量价弱正相关（r={r:.2f}），量价配合一般"
    if r > -0.3:
        return f"量价无明显相关（r={r:.2f}），近期资金情绪中性"
    if r > -0.6:
        return f"量价弱负相关（r={r:.2f}），涨时缩量或跌时放量，需警惕"
    return f"量价负相关（r={r:.2f}），量价背离明显，行情分歧较大"


# ── 公开工具函数 ───────────────────────────────────────────────────────────────

def get_price_volume_data(stock_code: str, days: int = 60, target_date: str | None = None) -> dict[str, Any]:
    """
    获取公司最近 N 个交易日的原始日行情序列。

    Args:
        stock_code: 6位股票代码
        days: 返回交易日数，默认60

    Returns:
        dict，包含：
        - stock_code / stock_name
        - count: 实际返回条数
        - trade_dates / close_prices / open_prices / high_prices / low_prices
        - volumes / amounts / change_pcts
        - latest: 最新一日行情摘要
    """
    container = ServiceContainer.build_default()
    company_res = container.company.get_company_basic_info(stock_code)
    stock_name = (
        company_res.data.get("stock_name", stock_code)
        if company_res.success and company_res.data
        else stock_code
    )

    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 60
    days = max(1, min(days, 500))

    from sqlalchemy import select, desc, func
    from app.core.database.models.financial_hot import FinancialHot, FinancialArchive

    def _latest_day_stmt(model):
        trade_day = func.coalesce(model.trade_date, model.report_date)
        return (
            select(func.max(trade_day))
            .where(
                model.stock_code == stock_code,
                func.lower(model.report_type) == "daily",
                model.close_price.isnot(None),
            )
        )

    db = SessionLocal()
    try:
        latest_candidates = [
            db.execute(_latest_day_stmt(FinancialHot)).scalar_one_or_none(),
            db.execute(_latest_day_stmt(FinancialArchive)).scalar_one_or_none(),
        ]
    finally:
        db.close()

    latest_available_day = max([day for day in latest_candidates if day is not None], default=None)
    default_year = latest_available_day.year if latest_available_day else datetime.now().year
    parsed_target_day = _parse_target_trade_date(target_date, default_year=default_year)

    def _daily_stmt(model):
        trade_day = func.coalesce(model.trade_date, model.report_date)
        stmt = (
            select(model)
            .where(
                model.stock_code == stock_code,
                func.lower(model.report_type) == "daily",
                model.close_price.isnot(None),
            )
            .order_by(desc(trade_day))
            .limit(days)
        )
        if parsed_target_day is not None:
            stmt = stmt.where(trade_day <= parsed_target_day)
        return stmt

    db = SessionLocal()
    try:
        hot_rows = db.execute(_daily_stmt(FinancialHot)).scalars().all()
        archive_rows = db.execute(_daily_stmt(FinancialArchive)).scalars().all()
    finally:
        db.close()

    by_day = {}
    for row in list(hot_rows) + list(archive_rows):
        row_day = _row_day(row)
        if row_day is None:
            continue
        by_day.setdefault(str(row_day), row)
    rows = sorted(
        by_day.values(),
        key=lambda row: _row_day(row),
        reverse=True,
    )[:days]

    if not rows:
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "error": "数据库中暂无该公司的日行情数据（financial_hot/financial_archive report_type='daily'）。",
            "count": 0,
        }

    rows = list(reversed(rows))  # 升序

    trade_dates = [str(_row_day(r)) for r in rows]
    close_prices = [float(r.close_price) for r in rows]
    open_prices = [float(r.open_price) if r.open_price else None for r in rows]
    high_prices = [float(r.high_price) if r.high_price else None for r in rows]
    low_prices = [float(r.low_price) if r.low_price else None for r in rows]
    volumes = [float(r.volume) if r.volume else None for r in rows]
    amounts = [float(r.amount) if r.amount else None for r in rows]
    change_pcts = [_change_pct_to_percent(r.change_pct) for r in rows]

    latest = rows[-1]
    result = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "requested_target_date": str(parsed_target_day) if parsed_target_day else None,
        "count": len(rows),
        "trade_dates": trade_dates,
        "close_prices": close_prices,
        "open_prices": open_prices,
        "high_prices": high_prices,
        "low_prices": low_prices,
        "volumes": volumes,
        "amounts": amounts,
        "change_pcts": change_pcts,
        "latest": {
            "date": str(latest.report_date),
            "close": float(latest.close_price),
            "change_pct": _change_pct_to_percent(latest.change_pct),
            "volume": float(latest.volume) if latest.volume else None,
        },
    }
    if parsed_target_day is not None:
        matched = latest
        matched_day = _row_day(matched)
        result["target_record"] = _row_payload(matched)
        result["target_match"] = {
            "requested_date": str(parsed_target_day),
            "matched_date": str(matched_day) if matched_day else None,
            "is_exact": matched_day == parsed_target_day,
            "note": "若 is_exact=false，说明目标日期不是交易日或库中缺该日数据，返回的是目标日前最近交易日。",
        }
    return result


def get_price_volume_analysis(stock_code: str, days: int = 60) -> dict[str, Any]:
    """
    量价技术分析：MA均线、量价相关系数、价格动量、量价信号检测。

    Args:
        stock_code: 6位股票代码
        days: 分析窗口，默认60个交易日

    Returns:
        dict，包含：
        - price_trend: MA5/10/20、当前价相对MA20的偏离、近5/10/20日动量
        - volume_trend: 量MA5/10、最新成交量相对量MA10的倍数
        - correlation: 近20日量价Pearson相关系数及解读
        - amplitude: 近期振幅均值
        - signals: 识别到的量价信号列表（最近10条）
        - summary: 综合量价判断
    """
    raw = get_price_volume_data(stock_code, days=max(days, 30))
    if "error" in raw:
        return raw

    closes = raw["close_prices"]
    vols = [v if v is not None else 0.0 for v in raw["volumes"]]
    dates = raw["trade_dates"]
    change_pcts = raw["change_pcts"]
    highs = raw["high_prices"]
    lows = raw["low_prices"]
    opens = raw["open_prices"]

    # ── 价格均线 ──
    ma5 = _ma(closes, 5)
    ma10 = _ma(closes, 10)
    ma20 = _ma(closes, 20)

    latest_close = closes[-1]
    latest_ma20 = ma20[-1]
    ma20_deviation = (
        round((latest_close - latest_ma20) / latest_ma20, 4)
        if latest_ma20 else None
    )

    # ── 量均线 ──
    vol_ma5 = _ma(vols, 5) if len(vols) >= 5 else [None] * len(vols)
    vol_ma10 = _ma(vols, 10) if len(vols) >= 10 else [None] * len(vols)
    latest_vol = vols[-1] if vols else None
    latest_vol_ma10 = vol_ma10[-1] if vol_ma10 else None
    vol_ratio = (
        round(latest_vol / latest_vol_ma10, 2)
        if latest_vol and latest_vol_ma10 and latest_vol_ma10 > 0
        else None
    )

    # ── 量价相关（近20日）──
    window = 20
    corr_closes = closes[-window:] if len(closes) >= window else closes
    corr_vols = vols[-window:] if len(vols) >= window else vols
    min_len = min(len(corr_closes), len(corr_vols))
    corr = _pearson(corr_closes[-min_len:], corr_vols[-min_len:])

    # ── 振幅均值（近20日）──
    amp_vals = []
    for i in range(max(0, len(closes) - 20), len(closes)):
        h = highs[i] if highs[i] else closes[i]
        l = lows[i] if lows[i] else closes[i]
        o = opens[i] if opens[i] else closes[i]
        if o and o > 0:
            amp_vals.append((h - l) / o)
    avg_amplitude = round(sum(amp_vals) / len(amp_vals), 4) if amp_vals else None

    # ── 量价信号检测 ──
    # change_pct 对外统一转成百分比单位：数据库值 * 100。
    signals: list[dict] = []
    for i in range(len(closes)):
        v = vols[i] if i < len(vols) else None
        vm10 = vol_ma10[i] if i < len(vol_ma10) else None
        chg = change_pcts[i] if i < len(change_pcts) else None
        if v is None or vm10 is None or chg is None or vm10 == 0:
            continue

        vol_r = v / vm10
        sig_type = None
        detail = None

        if vol_r > 1.5 and chg > 2.0:
            sig_type = "放量上涨"
            detail = f"成交量为均量{vol_r:.1f}倍，涨幅{chg:.2f}%，资金积极入场，趋势强化信号"
        elif vol_r > 1.5 and chg < -2.0:
            sig_type = "放量下跌"
            detail = f"成交量为均量{vol_r:.1f}倍，跌幅{abs(chg):.2f}%，抛压较重，注意风险"
        elif vol_r < 0.7 and chg > 1.0:
            sig_type = "缩量上涨"
            detail = f"成交量仅均量{vol_r:.1f}倍，涨幅{chg:.2f}%，量价背离，上涨持续性存疑"
        elif vol_r < 0.7 and chg < -1.0:
            sig_type = "缩量下跌"
            detail = f"成交量仅均量{vol_r:.1f}倍，跌幅{abs(chg):.2f}%，缩量企稳，可能筑底"

        if sig_type:
            signals.append({
                "date": dates[i],
                "type": sig_type,
                "close": closes[i],
                "change_pct": chg,
                "volume_ratio": round(vol_r, 2),
                "detail": detail,
            })

    # 只返回最近 10 条信号
    recent_signals = signals[-10:] if len(signals) > 10 else signals

    # ── 综合判断 ──
    bull_signals = sum(1 for s in signals[-20:] if s["type"] == "放量上涨")
    bear_signals = sum(1 for s in signals[-20:] if s["type"] == "放量下跌")
    diverge_up = sum(1 for s in signals[-20:] if s["type"] == "缩量上涨")

    if bull_signals > bear_signals + diverge_up and (corr or 0) > 0.3:
        summary = f"近期量价配合良好，放量上涨信号{bull_signals}次，量价趋势健康，多头占优。"
    elif bear_signals > bull_signals:
        summary = f"近期抛压信号偏多，放量下跌{bear_signals}次，需警惕进一步回调风险。"
    elif diverge_up > 2:
        summary = f"近期出现{diverge_up}次缩量上涨，量价背离，上涨动能不足，建议谨慎追涨。"
    elif (corr or 0) < -0.3:
        summary = "近期量价关系背离明显，行情分歧较大，建议观望等待方向明朗。"
    else:
        summary = "近期量价信号中性，无明显趋势特征，建议结合基本面综合判断。"

    return {
        "stock_code": stock_code,
        "stock_name": raw["stock_name"],
        "data_days": raw["count"],
        "latest": raw["latest"],
        "price_trend": {
            "ma5": ma5[-1],
            "ma10": ma10[-1],
            "ma20": ma20[-1],
            "ma20_deviation": ma20_deviation,
            "momentum_5d": _momentum(closes, 5),
            "momentum_10d": _momentum(closes, 10),
            "momentum_20d": _momentum(closes, 20),
        },
        "volume_trend": {
            "vol_ma5": round(vol_ma5[-1], 2) if vol_ma5[-1] else None,
            "vol_ma10": round(vol_ma10[-1], 2) if vol_ma10[-1] else None,
            "vol_ratio_latest": vol_ratio,
        },
        "correlation": {
            "pearson_20d": corr,
            "interpretation": _corr_interpretation(corr),
        },
        "amplitude": {
            "avg_amplitude_20d": avg_amplitude,
            "pct": f"{avg_amplitude*100:.2f}%" if avg_amplitude else "N/A",
        },
        "signals": recent_signals,
        "signal_stats": {
            "total": len(signals),
            "放量上涨": bull_signals,
            "放量下跌": bear_signals,
            "缩量上涨": diverge_up,
            "缩量下跌": sum(1 for s in signals[-20:] if s["type"] == "缩量下跌"),
        },
        "summary": summary,
    }


def get_price_volume_event_correlation(stock_code: str, days: int = 120) -> dict[str, Any]:
    """
    量价异动与公司公告/新闻事件关联分析。

    找出近 N 日内的量价异动点（成交量 > 均量1.5倍 且 涨跌幅绝对值 > 3%），
    并在异动日前后 ±3 天内检索相关公告和新闻，尝试解释异动原因。

    Args:
        stock_code: 6位股票代码
        days: 回溯天数，默认120

    Returns:
        dict，包含：
        - anomalies: 异动列表，每条含 date/price_change_pct/volume_ratio/type/nearby_events/interpretation
        - summary: 汇总结论
    """
    raw = get_price_volume_data(stock_code, days=days)
    if "error" in raw:
        return raw

    closes = raw["close_prices"]
    vols = [v if v else 0.0 for v in raw["volumes"]]
    dates = raw["trade_dates"]
    change_pcts = raw["change_pcts"]

    vol_ma10 = _ma(vols, 10)

    from datetime import date as date_type, timedelta
    from sqlalchemy import select, and_, or_
    from app.core.database.models.announcement_hot import AnnouncementHot
    from app.core.database.models.news_hot import NewsHot

    anomalies = []
    for i in range(len(closes)):
        vm10 = vol_ma10[i]
        v = vols[i]
        chg = change_pcts[i] or 0.0
        if vm10 is None or vm10 == 0:
            continue
        vol_r = v / vm10
        if vol_r < 1.5 or abs(chg) < 3.0:
            continue
        anom_type = "放量上涨" if chg > 0 else "放量下跌"
        anom_date = date_type.fromisoformat(dates[i])
        window_start = anom_date - timedelta(days=3)
        window_end = anom_date + timedelta(days=3)

        db = SessionLocal()
        try:
            anns = db.execute(
                select(AnnouncementHot.title, AnnouncementHot.publish_date, AnnouncementHot.announcement_type)
                .where(
                    AnnouncementHot.stock_code == stock_code,
                    AnnouncementHot.publish_date >= window_start,
                    AnnouncementHot.publish_date <= window_end,
                )
                .limit(3)
            ).all()

            news = db.execute(
                select(NewsHot.title, NewsHot.publish_time, NewsHot.news_type)
                .where(
                    NewsHot.related_stock_codes_json.contains(stock_code),
                    NewsHot.publish_time >= window_start,
                    NewsHot.publish_time <= window_end,
                )
                .limit(3)
            ).all()
        finally:
            db.close()

        nearby_events = []
        for a in anns:
            nearby_events.append({
                "date": str(a.publish_date),
                "type": "公告",
                "category": a.announcement_type or "",
                "title": a.title or "",
            })
        for n in news:
            nearby_events.append({
                "date": str(n.publish_time)[:10],
                "type": "新闻",
                "category": n.news_type or "",
                "title": n.title or "",
            })

        if nearby_events:
            event_titles = "、".join(e["title"][:20] for e in nearby_events[:2])
            interpretation = f"异动日附近发现{len(nearby_events)}条事件（{event_titles}等），可能是驱动{anom_type}的催化剂。"
        else:
            interpretation = f"异动日前后未找到明确公告或新闻，{anom_type}可能由市场情绪或大盘联动驱动。"

        anomalies.append({
            "date": dates[i],
            "close": closes[i],
            "price_change_pct": round(chg, 4),
            "volume_ratio": round(vol_r, 2),
            "type": anom_type,
            "nearby_events": nearby_events,
            "interpretation": interpretation,
        })

    explained = sum(1 for a in anomalies if a["nearby_events"])
    total = len(anomalies)
    if total == 0:
        summary = f"近{days}日内未发现显著量价异动（无成交量>均量1.5倍且涨跌幅>3%的记录）。"
    else:
        summary = (
            f"近{days}日共发现 {total} 次量价异动，其中 {explained} 次有对应公告或新闻事件，"
            f"事件解释率 {explained/total*100:.0f}%。"
            f"{'建议关注无法解释的异动，可能存在信息不对称风险。' if total - explained > 2 else ''}"
        )

    return {
        "stock_code": stock_code,
        "stock_name": raw["stock_name"],
        "days_analyzed": raw["count"],
        "anomaly_count": total,
        "anomalies": anomalies,
        "summary": summary,
    }


__all__ = [
    "get_price_volume_data",
    "get_price_volume_analysis",
    "get_price_volume_event_correlation",
]
