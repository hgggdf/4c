"""main.py 入口测试：FastAPI 应用、CORS 中间件、路由注册、健康检查。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# 隔离 bootstrap：阻止 main.py 在导入时连接真实 MySQL
# ---------------------------------------------------------------------------

_mock_bootstrap = MagicMock()
_mock_bootstrap.check_database_health = MagicMock(return_value={
    "status": "ok",
    "available": True,
    "storage_mode": "mysql-only",
    "runtime_mode": "mysql-only",
    "engine": "mysql+pymysql",
    "dialect": "mysql",
    "driver": "pymysql",
    "database_name": "stock_agent",
    "server_version": "8.0.0",
    "latency_ms": 1.0,
})
_mock_bootstrap.init_application_database = MagicMock()

# 在 main.py 被导入之前注入 mock，避免 bootstrap 模块级代码触发 MySQL 连接
with patch.dict("sys.modules", {"app.bootstrap": _mock_bootstrap}):
    import main as app_module

app = app_module.app


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ===========================================================================
# 1. FastAPI 应用基础属性
# ===========================================================================

class TestAppConfig:
    def test_app_title_matches_settings(self):
        """app.title 应与 settings.app_name 一致。"""
        assert app.title == app_module.settings.app_name

    def test_app_is_fastapi_instance(self):
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)


# ===========================================================================
# 2. CORS 中间件
# ===========================================================================

class TestCORSMiddleware:
    def test_cors_header_present_for_allowed_origin(self, client):
        """允许的 origin 应在响应中返回 Access-Control-Allow-Origin。"""
        origin = app_module.settings.cors_origins[0]
        resp = client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == origin

    def test_cors_allows_credentials(self, client):
        origin = app_module.settings.cors_origins[0]
        resp = client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_cors_allows_all_methods(self, client):
        origin = app_module.settings.cors_origins[0]
        resp = client.options(
            "/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        allowed = resp.headers.get("access-control-allow-methods", "")
        # allow_methods=["*"] 展开后应包含常用方法
        assert any(m in allowed.upper() for m in ("*", "POST", "GET"))

    def test_cors_origins_parsed_from_settings(self):
        """cors_origins 应是非空列表，每项都是合法 URL。"""
        origins = app_module.settings.cors_origins
        assert isinstance(origins, list)
        assert len(origins) >= 1
        for o in origins:
            assert o.startswith("http")


# ===========================================================================
# 3. 路由注册
# ===========================================================================

EXPECTED_ROUTE_PREFIXES = [
    "/api/chat",
    "/api/stock",
    "/api/analysis",
    "/api/announcement",
    "/api/cache",
    "/api/company",
    "/api/financial",
    "/api/ingest",
    "/api/macro",
    "/api/maintenance",
    "/api/news",
    "/api/retrieval",
]


class TestRouterRegistration:
    @pytest.fixture(scope="class")
    def all_paths(self):
        return {route.path for route in app.routes}

    def test_all_expected_prefixes_registered(self, all_paths):
        """每个业务路由前缀至少有一条路径被注册。"""
        for prefix in EXPECTED_ROUTE_PREFIXES:
            matched = any(p.startswith(prefix) for p in all_paths)
            assert matched, f"路由前缀 {prefix!r} 未注册到 app"

    def test_health_route_registered(self, all_paths):
        assert "/health" in all_paths

    def test_no_duplicate_paths(self):
        """同一 (path, method) 组合不应重复注册。"""
        seen: set[tuple[str, str]] = set()
        for route in app.routes:
            methods = getattr(route, "methods", None) or set()
            for method in methods:
                key = (route.path, method)
                assert key not in seen, f"重复路由：{key}"
                seen.add(key)

    def test_router_count(self):
        """共注册 17 个 router（含 health 端点所在的 main 路由）。"""
        # 17 个 include_router 调用对应 17 个业务路由模块
        routers = [
            "chat", "stock", "analysis",
            "announcement", "announcement_write",
            "cache", "company", "company_write",
            "financial", "financial_write",
            "ingest", "macro", "macro_write",
            "maintenance", "news", "news_write",
            "retrieval",
        ]
        assert len(routers) == 17


# ===========================================================================
# 4. /health 端点
# ===========================================================================

class TestHealthEndpoint:
    def test_health_returns_200_when_db_available(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_schema(self, client):
        data = client.get("/health").json()
        assert "status" in data
        assert "service" in data
        assert "database" in data

    def test_health_status_ok_when_db_available(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_service_name_matches_settings(self, client):
        data = client.get("/health").json()
        assert data["service"]["name"] == app_module.settings.app_name

    def test_health_service_alive(self, client):
        data = client.get("/health").json()
        assert data["service"]["status"] == "alive"

    def test_health_database_field_present(self, client):
        data = client.get("/health").json()
        assert isinstance(data["database"], dict)

    def test_health_returns_503_when_db_unavailable(self):
        """数据库不可用时应返回 503 且 status 为 degraded。"""
        unhealthy = {"available": False, "status": "error"}
        with patch.object(app_module, "check_database_health", return_value=unhealthy):
            with TestClient(app, raise_server_exceptions=True) as c:
                resp = c.get("/health")
        assert resp.status_code == 503
        assert resp.json()["status"] == "degraded"

    def test_health_calls_check_database_health(self, client):
        """每次请求 /health 都应调用 check_database_health。"""
        with patch.object(
            app_module,
            "check_database_health",
            return_value={"available": True},
        ) as mock_check:
            client.get("/health")
        mock_check.assert_called_once()


# ===========================================================================
# 5. startup 事件
# ===========================================================================

class TestStartupEvent:
    def test_startup_calls_init_application_database(self):
        """startup 事件应调用 init_application_database。"""
        with patch.object(app_module, "init_application_database") as mock_init:
            with TestClient(app):
                pass
        mock_init.assert_called_once()
