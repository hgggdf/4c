from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import requests


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from crawler.clients.akshare_client import StockDataProvider
from crawler.pipelines.financial_pipeline import build_financial_package_payload


def _post_json(url: str, payload: dict, timeout: int) -> tuple[int, dict | str]:
    response = requests.post(url, json=payload, timeout=timeout)
    try:
        body: dict | str = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body


def _response_message(body: dict | str) -> str:
    if isinstance(body, dict):
        return str(body.get("message") or body.get("error_code") or body)
    return str(body)


def _build_company_master_payload(dataset: dict, stock_code: str) -> dict:
    company_info = dataset.get("company_info") or {}
    stock_name = str(dataset.get("name") or stock_code).strip() or stock_code
    full_name = str(company_info.get("股票名称") or company_info.get("公司名称") or "").strip() or None
    exchange = str(dataset.get("exchange") or "").strip() or None
    aliases = dataset.get("aliases") or None
    return {
        "stock_code": stock_code,
        "stock_name": stock_name,
        "full_name": full_name,
        "exchange": exchange,
        "alias_json": aliases,
        "status": "active",
        "source_type": "crawler_stock_data_provider",
    }


def _ensure_company_master(stock_code: str, dataset: dict, *, base_url: str, timeout: int) -> tuple[int, dict | str]:
    status_code, response_body = _post_json(
        f"{base_url.rstrip('/')}/api/company-write/upsert-master",
        _build_company_master_payload(dataset, stock_code),
        timeout,
    )
    if status_code != 200:
        raise RuntimeError(f"company_master prewrite failed with HTTP {status_code}: {_response_message(response_body)}")
    if not isinstance(response_body, dict) or not response_body.get("success", False):
        raise RuntimeError(f"company_master prewrite failed: {_response_message(response_body)}")
    return status_code, response_body


def run_ingest(stock_code: str, *, base_url: str, sync_vector_index: bool, timeout: int) -> dict:
    provider = StockDataProvider()
    dataset = provider.collect_company_dataset(stock_code)
    master_status_code, master_response = _ensure_company_master(
        stock_code,
        dataset,
        base_url=base_url,
        timeout=timeout,
    )
    payload = build_financial_package_payload(dataset, stock_code, sync_vector_index=sync_vector_index)
    status_code, response_body = _post_json(
        f"{base_url.rstrip('/')}/api/ingest/financial-package",
        payload,
        timeout,
    )
    return {
        "stock_code": stock_code,
        "company_master_status_code": master_status_code,
        "company_master_created": isinstance(master_response, dict) and bool((master_response.get("data") or {}).get("created")),
        "financial_notes_count": len(payload["financial_notes"]),
        "sync_vector_index": sync_vector_index,
        "status_code": status_code,
        "response": response_body,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch financial dataset and ingest through the existing financial package API.")
    parser.add_argument("stock_codes", nargs="+", help="One or more stock codes, for example 600276")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    parser.add_argument("--no-sync-vector-index", action="store_false", dest="sync_vector_index", help="Disable vector sync")
    parser.set_defaults(sync_vector_index=True)
    args = parser.parse_args()

    results = [
        run_ingest(
            stock_code,
            base_url=args.base_url,
            sync_vector_index=args.sync_vector_index,
            timeout=args.timeout,
        )
        for stock_code in args.stock_codes
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()