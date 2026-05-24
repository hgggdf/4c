"""估值分析工具函数

提供 PE / PB / PS / PEG / EV·EBITDA / DCF 六种估值方法的计算与行业横向对比。
所有数值均来自本地数据库，不依赖外部 API。
"""

from __future__ import annotations

from typing import Any

from app.service.container import ServiceContainer


# ── 内部辅助 ──────────────────────────────────────────────────────────────────

def _latest_annual(periods: list[dict]) -> dict | None:
    """从多期财务数据中取最近一期年报。"""
    annuals = [p for p in periods if str(p.get("report_type", "")).strip() in ("年报", "annual")]
    if annuals:
        return sorted(annuals, key=lambda x: str(x.get("report_date", "")), reverse=True)[0]
    if periods:
        return sorted(periods, key=lambda x: str(x.get("report_date", "")), reverse=True)[0]
    return None


def _safe_div(a, b) -> float | None:
    try:
        if b is None or float(b) == 0:
            return None
        return round(float(a) / float(b), 4)
    except (TypeError, ValueError):
        return None


def _growth_rate(values: list[float | None]) -> float | None:
    """计算列表中最后一期相对第一期的复合年均增长率（CAGR）。"""
    clean = [v for v in values if v is not None and v > 0]
    if len(clean) < 2:
        return None
    n = len(clean) - 1
    try:
        return round((clean[-1] / clean[0]) ** (1 / n) - 1, 4)
    except (ZeroDivisionError, ValueError):
        return None


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.2f}%"


def _fmt_x(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.2f}x"


# ── 公开工具函数 ───────────────────────────────────────────────────────────────

def get_valuation_metrics(stock_code: str, current_price: float | None = None) -> dict[str, Any]:
    """
    计算公司核心估值指标：PE、PB、PS、PEG、EV/EBITDA。

    Args:
        stock_code: 6位股票代码，如 "600276"
        current_price: 当前股价（元）。若不传，自动取数据库最新收盘价。

    Returns:
        dict，包含：
        - stock_code / stock_name
        - price: 使用的股价及来源
        - pe:  市盈率（TTM）及解读
        - pb:  市净率及解读
        - ps:  市销率及解读
        - peg: PEG 及解读
        - ev_ebitda: EV/EBITDA 及解读
        - summary: 综合估值结论（高估/合理/低估 + 理由）
        - data_period: 基准财务期
        - warning: 数据缺失警告（如有）
    """
    container = ServiceContainer.build_default()
    warnings: list[str] = []

    # 1. 公司基础信息
    company_res = container.company.get_company_basic_info(stock_code)
    stock_name = company_res.data.get("stock_name", stock_code) if company_res.success and company_res.data else stock_code

    # 2. 财务汇总（最近4期）
    from app.service.requests import FinancialSummaryRequest
    fin_res = container.financial.get_financial_summary(
        FinancialSummaryRequest(stock_code=stock_code, period_count=4)
    )
    periods: list[dict] = []
    if fin_res.success and fin_res.data:
        periods = fin_res.data.get("income_statements") or []

    if not periods:
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "error": "数据库中暂无该公司财务数据，无法计算估值指标。",
        }

    latest = _latest_annual(periods)
    data_period = latest.get("report_date", "N/A") if latest else "N/A"

    # 3. 股价：优先使用传入值，其次取数据库最新收盘价
    price_source = "用户传入"
    if current_price is None:
        from sqlalchemy import select, desc
        from app.core.database.models.financial_hot import FinancialHot
        from app.core.database.session import SessionLocal
        db = SessionLocal()
        try:
            row = db.execute(
                select(FinancialHot.close_price, FinancialHot.trade_date)
                .where(FinancialHot.stock_code == stock_code, FinancialHot.close_price.isnot(None))
                .order_by(desc(FinancialHot.trade_date))
                .limit(1)
            ).first()
            if row and row.close_price:
                current_price = float(row.close_price)
                price_source = f"数据库收盘价 ({row.trade_date})"
            else:
                warnings.append("数据库中无股价数据，PE/PB/PS 无法计算，建议传入 current_price 参数。")
        finally:
            db.close()

    # 4. 取最新期财务数据
    net_profit   = latest.get("net_profit") if latest else None
    eps          = latest.get("eps") if latest else None
    revenue      = latest.get("revenue") if latest else None
    total_assets = latest.get("total_assets") if latest else None
    total_liab   = latest.get("total_liabilities") if latest else None
    op_cf        = latest.get("operating_cashflow") if latest else None
    rd_expense   = latest.get("rd_expense") if latest else None

    # 股东权益 = 总资产 - 总负债
    equity = None
    if total_assets is not None and total_liab is not None:
        equity = float(total_assets) - float(total_liab)

    # 估算总股本：净利润 / EPS（仅在 EPS 有效时）
    total_shares = None
    if eps and net_profit and float(eps) != 0:
        total_shares = abs(float(net_profit) / float(eps))

    # 5. 计算各指标
    result: dict[str, Any] = {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "data_period": data_period,
        "price": {"value": current_price, "source": price_source},
    }

    # PE（市盈率）= 股价 / EPS
    pe_value = _safe_div(current_price, eps) if current_price else None
    pe_interp = _interpret_pe(pe_value, stock_name)
    result["pe"] = {
        "value": pe_value,
        "formula": "股价 / 每股收益(EPS)",
        "eps": eps,
        "interpretation": pe_interp,
    }

    # PB（市净率）= 总市值 / 股东权益
    pb_value = None
    market_cap = None
    if current_price and total_shares:
        market_cap = current_price * total_shares
        pb_value = _safe_div(market_cap, equity)
    pb_interp = _interpret_pb(pb_value)
    result["pb"] = {
        "value": pb_value,
        "formula": "总市值 / 股东权益",
        "equity": equity,
        "interpretation": pb_interp,
    }

    # PS（市销率）= 总市值 / 营业收入
    ps_value = _safe_div(market_cap, revenue) if market_cap else None
    ps_interp = _interpret_ps(ps_value)
    result["ps"] = {
        "value": ps_value,
        "formula": "总市值 / 营业收入",
        "revenue": revenue,
        "interpretation": ps_interp,
    }

    # PEG = PE / 净利润增长率
    net_profits = [p.get("net_profit") for p in sorted(periods, key=lambda x: str(x.get("report_date", "")))]
    profit_cagr = _growth_rate([float(v) for v in net_profits if v is not None])
    peg_value = _safe_div(pe_value, profit_cagr * 100) if pe_value and profit_cagr and profit_cagr > 0 else None
    peg_interp = _interpret_peg(peg_value)
    result["peg"] = {
        "value": peg_value,
        "formula": "PE / 净利润年均增速(%)",
        "profit_cagr": profit_cagr,
        "interpretation": peg_interp,
    }

    # EV/EBITDA
    # EBITDA ≈ 营业利润 + 折旧摊销（此处用净利润×1.15近似，更精确需折旧数据）
    op_profit = latest.get("operating_profit") if latest else None
    ebitda = float(op_profit) * 1.15 if op_profit else None
    # EV = 市值 + 总负债 - 现金（现金用经营现金流近似）
    ev = None
    if market_cap and total_liab:
        cash_approx = abs(float(op_cf)) * 0.5 if op_cf else 0
        ev = market_cap + float(total_liab) - cash_approx
    ev_ebitda = _safe_div(ev, ebitda)
    ev_interp = _interpret_ev_ebitda(ev_ebitda)
    result["ev_ebitda"] = {
        "value": ev_ebitda,
        "formula": "企业价值(EV) / EBITDA",
        "ev": ev,
        "ebitda": ebitda,
        "interpretation": ev_interp,
    }

    # 6. 综合结论
    result["summary"] = _overall_valuation_summary(pe_value, pb_value, ps_value, peg_value, ev_ebitda, stock_name)

    if warnings:
        result["warnings"] = warnings

    return result


def get_dcf_valuation(
    stock_code: str,
    wacc: float = 0.10,
    terminal_growth: float = 0.03,
    forecast_years: int = 5,
) -> dict[str, Any]:
    """
    基于历史自由现金流的 DCF 估值（简化版）。

    Args:
        stock_code: 6位股票代码
        wacc: 加权平均资本成本，默认 10%（医药行业参考值）
        terminal_growth: 永续增长率，默认 3%
        forecast_years: 预测年数，默认 5 年

    Returns:
        dict，包含：
        - intrinsic_value_per_share: 每股内在价值（元）
        - total_intrinsic_value: 公司内在总价值（亿元）
        - historical_fcf: 历史自由现金流列表
        - fcf_growth_rate: 历史 FCF 复合增速
        - pv_forecast: 预测期现值之和
        - pv_terminal: 终值现值
        - assumptions: 使用的假设参数
        - margin_of_safety: 与当前股价的安全边际（需传入 current_price）
    """
    container = ServiceContainer.build_default()

    company_res = container.company.get_company_basic_info(stock_code)
    stock_name = company_res.data.get("stock_name", stock_code) if company_res.success and company_res.data else stock_code

    from app.service.requests import FinancialSummaryRequest
    fin_res = container.financial.get_financial_summary(
        FinancialSummaryRequest(stock_code=stock_code, period_count=8)
    )
    periods: list[dict] = []
    if fin_res.success and fin_res.data:
        periods = fin_res.data.get("income_statements") or []

    # 只取年报，按日期升序
    annuals = sorted(
        [p for p in periods if str(p.get("report_type", "")).strip() in ("年报", "annual")],
        key=lambda x: str(x.get("report_date", ""))
    )

    if len(annuals) < 2:
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "error": "DCF 估值需要至少 2 期年报数据，当前数据不足。",
        }

    # 历史 FCF = 经营现金流 - 资本支出（用投资现金流绝对值的40%近似资本支出）
    historical_fcf = []
    for p in annuals:
        op_cf = p.get("operating_cashflow")
        inv_cf = p.get("investing_cashflow")
        if op_cf is not None:
            capex = abs(float(inv_cf)) * 0.4 if inv_cf else 0
            fcf = float(op_cf) - capex
            historical_fcf.append({
                "period": p.get("report_date"),
                "operating_cashflow": op_cf,
                "capex_estimate": round(capex, 2),
                "fcf": round(fcf, 2),
            })

    if not historical_fcf:
        return {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "error": "现金流数据缺失，无法进行 DCF 估值。",
        }

    fcf_values = [item["fcf"] for item in historical_fcf]
    fcf_growth = _growth_rate([v for v in fcf_values if v > 0])
    # 预测增速：取历史增速与行业保守值 8% 的均值，上限 25%
    if fcf_growth and fcf_growth > 0:
        forecast_growth = min((fcf_growth + 0.08) / 2, 0.25)
    else:
        forecast_growth = 0.06

    base_fcf = fcf_values[-1]

    # 预测期现值
    pv_forecast = 0.0
    forecast_detail = []
    fcf_t = base_fcf
    for t in range(1, forecast_years + 1):
        fcf_t = fcf_t * (1 + forecast_growth)
        pv = fcf_t / (1 + wacc) ** t
        pv_forecast += pv
        forecast_detail.append({
            "year": f"第{t}年",
            "fcf": round(fcf_t, 2),
            "pv": round(pv, 2),
        })

    # 终值及其现值
    terminal_fcf = fcf_t * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1 + wacc) ** forecast_years

    total_value = pv_forecast + pv_terminal

    # 估算每股价值
    eps_latest = annuals[-1].get("eps") if annuals else None
    net_profit_latest = annuals[-1].get("net_profit") if annuals else None
    per_share_value = None
    if eps_latest and net_profit_latest and float(net_profit_latest) != 0:
        total_shares = abs(float(net_profit_latest) / float(eps_latest))
        per_share_value = round(total_value / total_shares, 2) if total_shares > 0 else None

    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "historical_fcf": historical_fcf,
        "fcf_growth_rate": fcf_growth,
        "forecast_growth_rate": forecast_growth,
        "forecast_detail": forecast_detail,
        "pv_forecast": round(pv_forecast, 2),
        "pv_terminal": round(pv_terminal, 2),
        "total_intrinsic_value": round(total_value, 2),
        "intrinsic_value_per_share": per_share_value,
        "assumptions": {
            "wacc": wacc,
            "terminal_growth": terminal_growth,
            "forecast_years": forecast_years,
            "forecast_fcf_growth": forecast_growth,
            "base_fcf": base_fcf,
        },
        "note": "资本支出采用投资现金流绝对值×40%估算，终值采用 Gordon 增长模型。建议结合 PE/PB 等多维指标综合判断。",
    }


def get_valuation_comparison(stock_codes: list[str]) -> dict[str, Any]:
    """
    对多家公司进行估值横向对比（基于 PE / PB / PS / ROE）。

    Args:
        stock_codes: 股票代码列表，最多 8 家

    Returns:
        dict，包含：
        - companies: 各公司估值指标汇总表
        - ranking: 综合估值吸引力排名（从高到低）
        - industry_avg: 各指标行业均值
        - conclusion: 对比结论
    """
    if len(stock_codes) > 8:
        stock_codes = stock_codes[:8]

    container = ServiceContainer.build_default()
    rows = []

    for sc in stock_codes:
        try:
            company_res = container.company.get_company_basic_info(sc)
            name = company_res.data.get("stock_name", sc) if company_res.success and company_res.data else sc

            from app.service.requests import FinancialSummaryRequest
            fin_res = container.financial.get_financial_summary(
                FinancialSummaryRequest(stock_code=sc, period_count=4)
            )
            periods = (fin_res.data.get("income_statements") or []) if fin_res.success and fin_res.data else []
            latest = _latest_annual(periods)

            if not latest:
                rows.append({"stock_code": sc, "stock_name": name, "error": "无财务数据"})
                continue

            net_profit = latest.get("net_profit")
            eps        = latest.get("eps")
            revenue    = latest.get("revenue")
            total_assets = latest.get("total_assets")
            total_liab   = latest.get("total_liabilities")
            equity = (float(total_assets) - float(total_liab)) if total_assets and total_liab else None
            roe    = latest.get("roe") or latest.get("net_margin")
            gross_margin = latest.get("gross_margin")
            rd_ratio     = latest.get("rd_ratio")

            # 取数据库最新收盘价
            from sqlalchemy import select as sa_select, desc
            from app.core.database.models.financial_hot import FinancialHot
            from app.core.database.session import SessionLocal
            db = SessionLocal()
            try:
                row = db.execute(
                    sa_select(FinancialHot.close_price)
                    .where(FinancialHot.stock_code == sc, FinancialHot.close_price.isnot(None))
                    .order_by(desc(FinancialHot.trade_date))
                    .limit(1)
                ).first()
                close_price = float(row.close_price) if row and row.close_price else None
            finally:
                db.close()

            total_shares = abs(float(net_profit) / float(eps)) if net_profit and eps and float(eps) != 0 else None
            market_cap   = close_price * total_shares if close_price and total_shares else None
            pe = _safe_div(close_price, eps) if close_price else None
            pb = _safe_div(market_cap, equity) if market_cap else None
            ps = _safe_div(market_cap, revenue) if market_cap else None

            net_profits = [p.get("net_profit") for p in sorted(periods, key=lambda x: str(x.get("report_date", "")))]
            profit_cagr = _growth_rate([float(v) for v in net_profits if v is not None])
            peg = _safe_div(pe, profit_cagr * 100) if pe and profit_cagr and profit_cagr > 0 else None

            rows.append({
                "stock_code": sc,
                "stock_name": name,
                "close_price": close_price,
                "pe": pe,
                "pb": pb,
                "ps": ps,
                "peg": peg,
                "roe": roe,
                "gross_margin": gross_margin,
                "rd_ratio": rd_ratio,
                "net_profit": net_profit,
                "revenue": revenue,
                "data_period": latest.get("report_date"),
            })
        except Exception as exc:
            rows.append({"stock_code": sc, "stock_name": sc, "error": str(exc)})

    valid = [r for r in rows if "error" not in r]

    # 行业均值
    def avg(key):
        vals = [r[key] for r in valid if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    industry_avg = {
        "pe": avg("pe"), "pb": avg("pb"), "ps": avg("ps"),
        "peg": avg("peg"), "roe": avg("roe"), "gross_margin": avg("gross_margin"),
    }

    # 综合吸引力评分：低 PE + 低 PB + 低 PEG + 高 ROE = 高分
    def score(r):
        s = 0
        avg_pe = industry_avg["pe"] or 30
        avg_pb = industry_avg["pb"] or 3
        avg_peg = industry_avg["peg"] or 1.5
        if r.get("pe") and r["pe"] < avg_pe: s += 2
        if r.get("pb") and r["pb"] < avg_pb: s += 2
        if r.get("peg") and r["peg"] < avg_peg: s += 2
        if r.get("peg") and r["peg"] < 1: s += 1
        if r.get("roe") and float(r["roe"]) > 0.15: s += 2
        if r.get("gross_margin") and float(r["gross_margin"]) > 0.50: s += 1
        return s

    ranking = sorted(valid, key=score, reverse=True)

    return {
        "companies": rows,
        "ranking": [
            {"rank": i + 1, "stock_code": r["stock_code"], "stock_name": r["stock_name"],
             "pe": r.get("pe"), "pb": r.get("pb"), "peg": r.get("peg"), "roe": r.get("roe")}
            for i, r in enumerate(ranking)
        ],
        "industry_avg": industry_avg,
        "conclusion": _comparison_conclusion(ranking, industry_avg),
    }


# ── 解读辅助函数 ───────────────────────────────────────────────────────────────

def _interpret_pe(pe: float | None, name: str = "") -> str:
    if pe is None:
        return "无法计算（缺少股价或 EPS 数据）"
    if pe < 0:
        return "公司当期亏损，PE 为负，无参考意义"
    if pe < 15:
        return f"PE {pe:.1f}x，处于低估区间，相对行业具备估值吸引力"
    if pe < 30:
        return f"PE {pe:.1f}x，估值合理，符合医药行业正常水平"
    if pe < 50:
        return f"PE {pe:.1f}x，估值偏高，需要业绩增速支撑"
    return f"PE {pe:.1f}x，估值较高，市场存在较强成长预期，风险偏大"


def _interpret_pb(pb: float | None) -> str:
    if pb is None:
        return "无法计算（缺少市值或净资产数据）"
    if pb < 1:
        return f"PB {pb:.2f}x，低于净资产，存在破净风险或价值低估"
    if pb < 3:
        return f"PB {pb:.2f}x，估值合理"
    if pb < 6:
        return f"PB {pb:.2f}x，偏高，需关注研发资产等无形资产的支撑"
    return f"PB {pb:.2f}x，显著偏高，适用于高 ROE 或强品牌溢价公司"


def _interpret_ps(ps: float | None) -> str:
    if ps is None:
        return "无法计算（缺少市值或营收数据）"
    if ps < 2:
        return f"PS {ps:.2f}x，偏低，适用于亏损期但营收增长快的公司"
    if ps < 6:
        return f"PS {ps:.2f}x，合理区间"
    return f"PS {ps:.2f}x，较高，需要高净利率或高增速支撑"


def _interpret_peg(peg: float | None) -> str:
    if peg is None:
        return "无法计算（净利润负增长或数据不足）"
    if peg < 0.8:
        return f"PEG {peg:.2f}，<1，成长性被低估，具备较强投资吸引力"
    if peg < 1.2:
        return f"PEG {peg:.2f}，≈1，估值与增速匹配，合理水平"
    if peg < 2:
        return f"PEG {peg:.2f}，>1，估值相对增速偏贵，需审慎"
    return f"PEG {peg:.2f}，>2，增速难以支撑当前估值，高风险"


def _interpret_ev_ebitda(ev_ebitda: float | None) -> str:
    if ev_ebitda is None:
        return "无法计算（数据不足）"
    if ev_ebitda < 10:
        return f"EV/EBITDA {ev_ebitda:.1f}x，低估值，具备并购吸引力"
    if ev_ebitda < 20:
        return f"EV/EBITDA {ev_ebitda:.1f}x，合理区间"
    if ev_ebitda < 35:
        return f"EV/EBITDA {ev_ebitda:.1f}x，偏高，适用于高成长标的"
    return f"EV/EBITDA {ev_ebitda:.1f}x，估值较贵，需强劲业绩增长支撑"


def _overall_valuation_summary(pe, pb, ps, peg, ev_ebitda, name: str) -> str:
    signals: list[str] = []
    bullish = 0
    bearish = 0

    if pe is not None and pe > 0:
        if pe < 20: bullish += 2
        elif pe < 35: bullish += 1
        else: bearish += 1

    if pb is not None:
        if pb < 3: bullish += 1
        elif pb > 6: bearish += 1

    if peg is not None:
        if peg < 1: bullish += 2
        elif peg > 2: bearish += 2
        else: bullish += 1

    if ev_ebitda is not None:
        if ev_ebitda < 15: bullish += 1
        elif ev_ebitda > 30: bearish += 1

    if bullish >= 4:
        verdict = "低估"
        signals.append(f"多项指标显示{name}当前处于低估区间，具备较强配置价值。")
    elif bullish >= 2 and bearish <= 1:
        verdict = "合理"
        signals.append(f"{name}估值整体合理，与基本面基本匹配。")
    elif bearish >= 3:
        verdict = "高估"
        signals.append(f"多项指标显示{name}当前估值偏高，需警惕回调风险。")
    else:
        verdict = "中性"
        signals.append(f"{name}估值指标分化，建议结合业绩增速和行业对比综合判断。")

    return f"【综合判断：{verdict}】" + "".join(signals)


def _comparison_conclusion(ranking: list[dict], avg: dict) -> str:
    if not ranking:
        return "数据不足，无法得出对比结论。"
    top = ranking[0]
    bottom = ranking[-1] if len(ranking) > 1 else None
    text = f"综合估值吸引力排名第一为【{top['stock_name']}】"
    if top.get("pe") and avg.get("pe"):
        diff = (top["pe"] - avg["pe"]) / avg["pe"] * 100
        text += f"（PE 较均值{'高' if diff > 0 else '低'} {abs(diff):.1f}%）"
    if bottom:
        text += f"，估值相对最贵的为【{bottom['stock_name']}】"
    text += "。建议结合各公司研发管线和业绩增速综合判断配置优先级。"
    return text


__all__ = [
    "get_valuation_metrics",
    "get_dcf_valuation",
    "get_valuation_comparison",
]
