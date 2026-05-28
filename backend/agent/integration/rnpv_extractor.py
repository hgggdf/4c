"""
LLM-based rNPV parameter extractor for uploaded documents.

Sends up to 6000 chars of document text to Kimi and parses a structured
JSON response containing pipeline fields needed for rNPV calculation.
Results are cached in-process keyed by doc_id so dialogue_agent can
use them as prefill without re-running the extraction.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from typing import Any

logger = logging.getLogger(__name__)

# ── In-process cache: doc_id -> extracted params dict ────────────────────────
_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}  # doc_id -> params


def get_cached_params(doc_id: str) -> dict[str, Any] | None:
    with _lock:
        return _cache.get(doc_id)


def get_all_cached_params() -> dict[str, dict[str, Any]]:
    """Return a shallow copy of the full cache (for merging multiple docs)."""
    with _lock:
        return dict(_cache)


def _set_cache(doc_id: str, params: dict[str, Any]) -> None:
    with _lock:
        _cache[doc_id] = params


# ── Extraction prompt ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are a pharmaceutical investment analyst assistant. "
    "Extract pipeline drug parameters from the document text provided by the user. "
    "Return ONLY a valid JSON object with these keys (omit keys you cannot find):\n"
    "  drug_name         (string) primary drug name\n"
    "  indication        (string) primary indication / disease\n"
    "  trial_phase       (string) one of: phase1 phase2 phase3 phase2_3 nda approved\n"
    "  expected_approval_year (integer) estimated NDA approval year\n"
    "  target_patients_wan   (number)  target patient population in wan (10k) persons\n"
    "  price_per_year_wan    (number)  annual treatment cost in wan CNY per patient\n"
    "  peak_market_share     (number)  peak market share as a decimal (e.g. 0.15)\n"
    "  route_of_administration (string) e.g. oral / injectable\n"
    "Do not add any explanation outside the JSON object."
)

_PHASE_NORMALIZE = {
    "i": "phase1", "phase i": "phase1", "phase1": "phase1",
    "ii": "phase2", "phase ii": "phase2", "phase2": "phase2",
    "iii": "phase3", "phase iii": "phase3", "phase3": "phase3",
    "ii/iii": "phase2_3", "2/3": "phase2_3",
    "nda": "nda", "bla": "nda",
    "approved": "approved",
}


def _normalize_phase(raw: str | None) -> str | None:
    if not raw:
        return None
    key = str(raw).strip().lower()
    return _PHASE_NORMALIZE.get(key, key if key.startswith("phase") else None)


def _parse_llm_response(text: str) -> dict[str, Any]:
    """Extract and parse the JSON object from LLM output."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    # Find the first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        logger.debug("rnpv_extractor: JSON parse failed on: %.200s", text)
        return {}

    result: dict[str, Any] = {}

    if data.get("drug_name"):
        result["drug_name"] = str(data["drug_name"]).strip()

    if data.get("indication"):
        result["indication"] = str(data["indication"]).strip()

    phase = _normalize_phase(data.get("trial_phase"))
    if phase:
        result["trial_phase"] = phase

    year = data.get("expected_approval_year")
    if year:
        try:
            y = int(year)
            if 2020 <= y <= 2050:
                result["expected_approval_year"] = y
        except (ValueError, TypeError):
            pass

    patients = data.get("target_patients_wan")
    if patients is not None:
        try:
            v = float(patients)
            if 0.1 <= v <= 50000:
                result["target_patients_wan"] = v
        except (ValueError, TypeError):
            pass

    price = data.get("price_per_year_wan")
    if price is not None:
        try:
            v = float(price)
            if 0.01 <= v <= 10000:
                result["price_per_year_wan"] = v
        except (ValueError, TypeError):
            pass

    share = data.get("peak_market_share")
    if share is not None:
        try:
            v = float(share)
            if v > 1:
                v = v / 100
            if 0 < v <= 1:
                result["peak_market_share"] = v
        except (ValueError, TypeError):
            pass

    if data.get("route_of_administration"):
        result["route_of_administration"] = str(data["route_of_administration"]).strip()

    return result


def extract_rnpv_params(doc_id: str, text: str) -> dict[str, Any]:
    """
    Call Kimi to extract rNPV parameters from document text.
    Result is stored in the in-process cache and also returned.
    Falls back to empty dict if LLM is not configured or call fails.
    """
    try:
        from agent.llm_clients.kimi_client import KimiClient
        client = KimiClient()
        if not client.is_configured():
            logger.debug("rnpv_extractor: Kimi not configured, skipping extraction")
            return {}

        # Truncate to avoid excessive token usage; first 6000 chars carry most pipeline info
        truncated = text[:6000]

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": truncated},
        ]
        raw = client.chat(messages, temperature=0.1, max_tokens=512)
        params = _parse_llm_response(raw)
        logger.info("rnpv_extractor: doc_id=%s extracted fields=%s", doc_id, list(params.keys()))
        _set_cache(doc_id, params)
        return params
    except Exception as exc:
        logger.warning("rnpv_extractor: extraction failed for doc_id=%s: %s", doc_id, exc)
        return {}


def extract_rnpv_params_async(doc_id: str, text: str) -> None:
    """Run extraction in a background thread so upload response is not delayed."""
    t = threading.Thread(target=extract_rnpv_params, args=(doc_id, text), daemon=True)
    t.start()
