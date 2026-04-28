"""蝴蝶效应分析器 — LLM 全权推理版。

行业传导和公司影响完全由 Kimi 推理，不走硬编码规则表。
每次分析的结构化结果通过回调写入 NewsHot.key_fields_json，
积累足够数据后可从中提炼规则。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Generator

from agent.llm_clients import KimiClient

logger = logging.getLogger(__name__)

# LLM 推理时可用的冲击类型枚举（仅作提示，不限制 LLM 输出）
_SHOCK_HINT = [
    "oil_price_surge", "usd_strength", "supply_chain_disruption",
    "risk_aversion", "energy_price_surge", "global_trade_restriction",
    "inflation_surge", "domestic_substitution", "policy_tightening",
    "interest_rate_hike", "pandemic_risk", "other",
]

_PHARMA_INDUSTRIES = [
    "原料药", "化学制药", "中药", "生物制品", "医疗器械",
    "CXO", "创新药", "医疗服务", "医药商业", "体外诊断",
]


class ButterflyAnalyzer:
    """蝴蝶效应分析器，LLM 全权推理，支持流式输出。"""

    def __init__(self) -> None:
        self.llm = KimiClient()

    def is_configured(self) -> bool:
        return self.llm.is_configured()

    # ── 公开接口 ──────────────────────────────────────────────────────────

    def analyze_stream(
        self,
        event_text: str,
        *,
        company_exposures: list[dict] | None = None,
        on_result: Callable[[dict], None] | None = None,
    ) -> Generator[dict, None, None]:
        """流式分析入口。

        on_result: 分析完成后回调，接收完整结构化结果，供调用方写库。

        SSE 事件类型：
          status        — 进度提示
          event_parsed  — 事件解析结果
          chain_node    — 传导链节点 level=industry|company
          risk_alert    — 风险预警
          opportunity   — 机会提示
          narrative_chunk — LLM 叙述性报告（流式）
          done          — 结束
        """
        if not self.is_configured():
            yield {"type": "error", "message": "Kimi 未配置，请检查 KIMI_API_KEY"}
            return

        # ── Step 1: 解析事件 ──────────────────────────────────────────────
        yield {"type": "status", "content": "正在解析事件结构…"}
        parsed = self._parse_event(event_text)
        yield {"type": "event_parsed", "data": parsed}

        # ── Step 2: LLM 推理行业传导 ──────────────────────────────────────
        yield {"type": "status", "content": "正在推演行业传导链…"}
        industry_impacts = self._infer_industry_impacts(event_text, parsed)
        for node in industry_impacts:
            yield {"type": "chain_node", "level": "industry", "data": node}

        # ── Step 3: LLM 推理公司暴露度 ───────────────────────────────────
        risk_alerts: list[dict] = []
        opportunity_alerts: list[dict] = []

        if company_exposures:
            yield {"type": "status", "content": "正在评估受影响公司…"}
            company_nodes = self._infer_company_impacts(
                event_text, parsed, industry_impacts, company_exposures
            )
            for node in company_nodes:
                yield {"type": "chain_node", "level": "company", "data": node}
                if node["direction"] == "negative" and node["exposure_score"] >= 0.5:
                    risk_alerts.append(node)
                elif node["direction"] == "positive" and node["exposure_score"] >= 0.4:
                    opportunity_alerts.append(node)

        for alert in sorted(risk_alerts, key=lambda x: x["exposure_score"], reverse=True)[:5]:
            yield {"type": "risk_alert", "data": alert}
        for opp in sorted(opportunity_alerts, key=lambda x: x["exposure_score"], reverse=True)[:3]:
            yield {"type": "opportunity", "data": opp}

        # ── Step 4: 叙述性报告 ────────────────────────────────────────────
        yield {"type": "status", "content": "正在生成分析报告…"}
        narrative_chunks: list[str] = []
        for chunk_event in self._generate_narrative_stream(
            event_text, parsed, industry_impacts, risk_alerts, opportunity_alerts
        ):
            narrative_chunks.append(chunk_event.get("content", ""))
            yield chunk_event

        # ── Step 5: 回调写库 ──────────────────────────────────────────────
        if on_result is not None:
            full_result = {
                "event_text": event_text,
                "event_parsed": parsed,
                "industry_impacts": industry_impacts,
                "risk_alerts": risk_alerts,
                "opportunity_alerts": opportunity_alerts,
                "narrative": "".join(narrative_chunks),
            }
            try:
                on_result(full_result)
            except Exception as exc:
                logger.warning("on_result callback failed: %s", exc)

        yield {"type": "done"}

    # ── 事件解析 ──────────────────────────────────────────────────────────

    def _parse_event(self, event_text: str) -> dict:
        prompt = f"""你是医药行业投研分析师。将以下宏观事件解析为结构化 JSON，严格按格式输出，不要有任何额外文字。

事件：{event_text}

参考冲击类型（可自由扩展）：{json.dumps(_SHOCK_HINT, ensure_ascii=False)}

输出格式：
{{
  "event_summary": "一句话概括",
  "event_type": "geopolitical|economic|policy|natural_disaster|other",
  "primary_shocks": ["shock_type1", ...],
  "affected_regions": ["中国", "全球", ...],
  "time_horizon": "short_term|mid_term|long_term",
  "severity": "high|medium|low",
  "confidence": 0.0~1.0
}}"""
        try:
            raw = self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=1.0,
                max_tokens=512,
            )
            return _extract_json(raw) or _fallback_parse(event_text)
        except Exception as exc:
            logger.warning("_parse_event failed: %s", exc)
            return _fallback_parse(event_text)

    # ── LLM 推理行业传导 ──────────────────────────────────────────────────

    def _infer_industry_impacts(self, event_text: str, parsed: dict) -> list[dict]:
        """让 LLM 直接推理每个医药子行业受到的影响，不走规则表。"""
        shocks_str = "、".join(parsed.get("primary_shocks", [])) or "未知冲击"
        industries_str = "、".join(_PHARMA_INDUSTRIES)

        prompt = f"""你是医药行业资深投研分析师。

宏观事件：{parsed.get('event_summary', event_text)}
主要冲击：{shocks_str}
影响时限：{parsed.get('time_horizon', 'short_term')}
严重程度：{parsed.get('severity', 'medium')}

请分析以下医药子行业受到的影响：{industries_str}

对每个受影响的子行业（跳过影响极小的），输出 JSON 数组，每条格式：
{{
  "industry": "子行业名称",
  "direction": "negative|positive|mixed",
  "strength": 0.0~1.0,
  "transmission_path": "传导路径一句话描述",
  "key_risks": ["风险点1", "风险点2"],
  "key_opportunities": ["机会点1"]
}}

只输出 JSON 数组，不要其他文字。"""

        try:
            raw = self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=1.0,
                max_tokens=1024,
            )
            result = _extract_json_array(raw)
            if result:
                return sorted(result, key=lambda x: x.get("strength", 0), reverse=True)
        except Exception as exc:
            logger.warning("_infer_industry_impacts failed: %s", exc)

        return []

    # ── LLM 推理公司暴露度 ────────────────────────────────────────────────

    def _infer_company_impacts(
        self,
        event_text: str,
        parsed: dict,
        industry_impacts: list[dict],
        company_exposures: list[dict],
    ) -> list[dict]:
        """让 LLM 结合公司财务特征推理每家公司的暴露度，分批处理避免超长。"""
        industry_context = "\n".join(
            f"- {n['industry']}：{n['direction']} 影响，强度 {n.get('strength', 0):.0%}，{n.get('transmission_path', '')}"
            for n in industry_impacts[:8]
        )

        all_results: list[dict] = []
        # 每批最多 15 家，避免 prompt 过长
        batch_size = 15
        for i in range(0, len(company_exposures), batch_size):
            batch = company_exposures[i: i + batch_size]
            batch_results = self._infer_company_batch(
                parsed, industry_context, batch
            )
            all_results.extend(batch_results)

        return sorted(all_results, key=lambda x: x.get("exposure_score", 0), reverse=True)

    def _infer_company_batch(
        self,
        parsed: dict,
        industry_context: str,
        batch: list[dict],
    ) -> list[dict]:
        companies_str = "\n".join(
            f"- {c['stock_name']}（{c['stock_code']}）子行业：{c.get('industry_level2', '未知')}，"
            f"毛利率：{_fmt_pct(c.get('gross_margin'))}，"
            f"研发费用率：{_fmt_pct(c.get('rd_ratio'))}，"
            f"资产负债率：{_fmt_pct(c.get('debt_ratio'))}，"
            f"成本率：{_fmt_pct(c.get('operating_cost_ratio'))}"
            for c in batch
        )

        prompt = f"""宏观事件：{parsed.get('event_summary', '')}（严重程度：{parsed.get('severity', 'medium')}）

行业传导结论：
{industry_context}

以下公司的财务特征：
{companies_str}

请结合行业传导结论和各公司财务特征，评估每家公司受到的影响。
只对所属子行业在传导结论中出现的公司进行评估，其余跳过。

输出 JSON 数组，每条格式：
{{
  "stock_code": "代码",
  "stock_name": "名称",
  "industry_level2": "子行业",
  "direction": "negative|positive|mixed",
  "exposure_score": 0.0~1.0,
  "reason": "一句话说明暴露原因",
  "financial_flags": ["财务特征标注，如低毛利率、高负债等"]
}}

只输出 JSON 数组，不要其他文字。"""

        try:
            raw = self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=1.0,
                max_tokens=1500,
            )
            result = _extract_json_array(raw)
            return result or []
        except Exception as exc:
            logger.warning("_infer_company_batch failed: %s", exc)
            return []

    # ── 叙述性报告（流式）────────────────────────────────────────────────

    def _generate_narrative_stream(
        self,
        event_text: str,
        parsed: dict,
        industry_impacts: list[dict],
        risk_alerts: list[dict],
        opportunity_alerts: list[dict],
    ) -> Generator[dict, None, None]:
        industry_summary = "\n".join(
            f"- {n['industry']}：{n['direction']} 影响 {n.get('strength', 0):.0%}，{n.get('transmission_path', '')}"
            for n in industry_impacts[:6]
        ) or "暂无行业传导数据"

        risk_summary = "\n".join(
            f"- {a['stock_name']}（{a['stock_code']}）暴露度 {a.get('exposure_score', 0):.0%}：{a.get('reason', '')}"
            for a in risk_alerts[:5]
        ) or "暂无高风险公司"

        opp_summary = "\n".join(
            f"- {a['stock_name']}（{a['stock_code']}）受益度 {a.get('exposure_score', 0):.0%}：{a.get('reason', '')}"
            for a in opportunity_alerts[:3]
        ) or "暂无明显受益公司"

        system = (
            "你是医药行业资深投研分析师。基于提供的结构化数据撰写预警报告，"
            "使用 Markdown 格式，专业简洁，禁止编造数据。"
        )
        user = f"""请基于以下分析结果撰写「蝴蝶效应预警报告」：

## 触发事件
{parsed.get('event_summary', event_text)}
- 类型：{parsed.get('event_type', '未知')} | 时限：{parsed.get('time_horizon', '')} | 严重程度：{parsed.get('severity', '')}

## 行业传导
{industry_summary}

## 风险预警公司
{risk_summary}

## 潜在受益公司
{opp_summary}

请输出：
1. 事件背景与传导逻辑（2-3句）
2. 重点关注行业及原因
3. 需警惕的公司及具体风险点
4. 潜在受益方向
5. 投资者行动建议（1-2条）"""

        try:
            for chunk in self.llm.chat_stream(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=1.0,
                max_tokens=1500,
            ):
                yield {"type": "narrative_chunk", "content": chunk}
        except Exception as exc:
            logger.exception("Narrative generation failed")
            yield {"type": "narrative_chunk", "content": f"\n（报告生成异常：{exc}）"}


# ── 工具函数 ──────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None


def _extract_json_array(text: str) -> list | None:
    start, end = text.find("["), text.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None


def _fallback_parse(event_text: str) -> dict:
    shocks = []
    text = event_text.lower()
    if any(k in text for k in ["战争", "冲突", "开战", "军事"]):
        shocks += ["oil_price_surge", "supply_chain_disruption", "risk_aversion"]
    if any(k in text for k in ["油价", "石油", "能源"]):
        shocks += ["oil_price_surge", "energy_price_surge"]
    if any(k in text for k in ["美元", "汇率", "贬值"]):
        shocks += ["usd_strength"]
    if any(k in text for k in ["贸易", "制裁", "关税"]):
        shocks += ["global_trade_restriction"]
    if any(k in text for k in ["通胀", "物价", "cpi"]):
        shocks += ["inflation_surge"]
    return {
        "event_summary": event_text[:80],
        "event_type": "other",
        "primary_shocks": list(dict.fromkeys(shocks)) or ["risk_aversion"],
        "affected_regions": ["全球"],
        "time_horizon": "short_term",
        "severity": "medium",
        "confidence": 0.5,
    }


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.1%}"
    except (TypeError, ValueError):
        return "N/A"


__all__ = ["ButterflyAnalyzer"]
