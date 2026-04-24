# 数据采集范围与映射说明

> 版本：1.0  
> 更新日期：2026-04-23  
> 维护目录：`backend/crawler/configs/`

本文档明确当前项目固定采集的**公司范围、时间窗口、数据来源、落盘路径、以及最终入库链路**，作为后续所有采集开发、 pipeline 开发、调度任务开发的唯一依据。

---

## 1. 固定公司范围（10 家）

行业聚焦：**医药生物（申万一级）**

| 序号 | 股票代码 | 股票简称 | 交易所 | 公司全称 |
|------|----------|----------|--------|----------|
| 1 | 600276 | 恒瑞医药 | SSE | 江苏恒瑞医药股份有限公司 |
| 2 | 300122 | 智飞生物 | SZSE | 重庆智飞生物制品股份有限公司 |
| 3 | 600436 | 片仔癀 | SSE | 漳州片仔癀药业股份有限公司 |
| 4 | 300760 | 迈瑞医疗 | SZSE | 深圳迈瑞生物医疗电子股份有限公司 |
| 5 | 002223 | 鱼跃医疗 | SZSE | 江苏鱼跃医疗设备股份有限公司 |
| 6 | 300832 | 新产业 | SZSE | 深圳市新产业生物医学工程股份有限公司 |
| 7 | 300676 | 华大基因 | SZSE | 深圳华大基因股份有限公司 |
| 8 | 603259 | 药明康德 | SSE | 无锡药明康德新药开发股份有限公司 |
| 9 | 300015 | 爱尔眼科 | SZSE | 爱尔眼科医院集团股份有限公司 |
| 10 | 600998 | 九州通 | SSE | 九州通医药集团股份有限公司 |

**配置源文件**：`backend/crawler/configs/company_universe.yaml`

---

## 2. 每类数据时间范围

| 数据类别 | 时间窗口 | 说明 |
|----------|----------|------|
| 公告 | 30 天 | 含定期报告、临时公告 |
| 个股研报 | 30 天 | — |
| 行业研报 | 30 天 | — |
| 新闻舆情 | 30 天 | — |
| 专利 | 30 天 | Schema Gap，暂不落库 |
| 日线行情 | 90 天 | 开盘价、收盘价、最高价、最低价、成交量、成交额 |
| 财务三表 | 365 天 | 利润表、资产负债表、现金流量表 |
| 财务附注 | 365 天 | — |
| 主营分部 | 365 天 | — |
| 财务指标 | 365 天 | 毛利率、ROE 等计算值 |
| 宏观指标 | 365 天 | 月度/季度发布 |

**配置源文件**：`backend/crawler/configs/data_time_windows.yaml`

---

## 3. 每个来源抓什么

| 来源 ID | 来源名称 | 抓取数据类别 | 访问方式 | 原始落盘目录 |
|---------|----------|--------------|----------|--------------|
| sse | 上海证券交易所 | 公告、定期报告 PDF | web_page | `raw/announcements/sse/` |
| szse | 深圳证券交易所 | 公告、定期报告 PDF | web_page | `raw/announcements/szse/` |
| bse | 北京证券交易所 | 公告、定期报告 PDF | web_page | `raw/announcements/bse/` |
| eastmoney_research | 东方财富研报中心 | 个股研报、行业研报 | api | `raw/research_reports/eastmoney/` |
| stats_gov | 国家统计局 | 宏观指标 | api | `raw/macro/stats_gov/` |
| cnipa | 国家知识产权局 | 专利 | web_page | `raw/patents/cnipa/` |
| stcn | 证券时报网 | 新闻 | web_page | `raw/news/stcn/` |
| cnstock | 中国证券网 | 新闻 | web_page | `raw/news/cnstock/` |
| cscom | 中证网 | 新闻 | web_page | `raw/news/cscom/` |
| akshare | AKShare | 行情、财务三表、附注、分部、指标 | python_sdk | `raw/financial_data/akshare/` |
| tushare | Tushare Pro | 行情、财务三表、指标 | api | `raw/financial_data/tushare/` |

**配置源文件**：`backend/crawler/configs/source_catalog.yaml`

---

## 4. 数据流转路径：raw → staging → ingest

```
[来源] → raw/目录（原始落盘） → pipeline（清洗/结构化） → staging/文件（ingest-ready） → /api/ingest/* → MySQL
```

### 4.1 各类数据的 raw 落盘目录

| 数据类别 | raw 落盘路径（相对 crawler/） |
|----------|-------------------------------|
| 公司基础信息 | `raw/company/master.json` |
| 公司经营概况 | `raw/company/profile.json` |
| 行业主数据 | `raw/company/industries.json` |
| 利润表 | `raw/financial_data/income_statements.json` |
| 资产负债表 | `raw/financial_data/balance_sheets.json` |
| 现金流量表 | `raw/financial_data/cashflow_statements.json` |
| 财务指标 | `raw/financial_data/financial_metrics.json` |
| 财务附注 | `raw/financial_data/financial_notes.json` |
| 主营分部 | `raw/financial_data/business_segments.json` |
| 日线行情 | `raw/financial_data/stock_daily.json` |
| 公告原文 | `raw/announcements/merged_announcements.json` |
| 结构化公告 | `raw/announcements/structured_announcements.json` |
| 药品审批 | `raw/announcements/drug_approvals.json` |
| 临床试验 | `raw/announcements/clinical_trials.json` |
| 集中采购 | `raw/announcements/procurement_events.json` |
| 监管风险 | `raw/announcements/regulatory_risks.json` |
| 新闻原文 | `raw/news/merged_news.json` |
| 结构化新闻 | `raw/news/structured_news.json` |
| 新闻-行业映射 | `raw/news/news_industry_maps.json` |
| 新闻-公司映射 | `raw/news/news_company_maps.json` |
| 行业影响事件 | `raw/news/industry_impact_events.json` |
| 宏观指标 | `raw/macro/macro_indicators.json` |
| 专利 | `raw/patents/cnipa_patents.json` |

### 4.2 staging 文件推荐位置

沿用现有 `crawler/staging/` 结构，按数据类别分文件：

| 数据类别 | staging 文件（相对 crawler/） |
|----------|-------------------------------|
| 公司主数据 | `staging/company_package.json` |
| 财务数据 | `staging/financial_package.json` |
| 公告数据 | `staging/announcement_package.json` |
| 新闻与宏观 | `staging/news_package.json` |
| 研报 | `staging/research_reports_*.json`（沿用现有命名惯例） |
| 专利 | `staging/patent_package.json`（暂不落库，仅 staging） |

---

## 5. Ingest Package 映射

当前后端提供 4 个 ingest 入口，每个入口对应固定的数据字段：

### 5.1 company-package → `/api/ingest/company-package`

| 数据类别 | ingest 字段 | 目标表 |
|----------|-------------|--------|
| 公司基础信息 | `company_master` | `company_master` |
| 公司经营概况 | `company_profile` | `company_profile` |
| 行业主数据 | `industries` | `industry_master` |
| 公司与行业映射 | `company_industries` | `company_industry_map` |

### 5.2 financial-package → `/api/ingest/financial-package`

| 数据类别 | ingest 字段 | 目标表 |
|----------|-------------|--------|
| 利润表 | `income_statements` | `income_statement_hot` |
| 资产负债表 | `balance_sheets` | `balance_sheet_hot` |
| 现金流量表 | `cashflow_statements` | `cashflow_statement_hot` |
| 财务指标 | `financial_metrics` | `financial_metric_hot` |
| 财务附注 | `financial_notes` | `financial_notes_hot` |
| 主营分部 | `business_segments` | `business_segment_hot` |
| 日线行情 | `stock_daily` | `stock_daily_hot` |

### 5.3 announcement-package → `/api/ingest/announcement-package`

| 数据类别 | ingest 字段 | 目标表 |
|----------|-------------|--------|
| 公告原文 | `raw_announcements` | `announcement_raw_hot` |
| 结构化公告 | `structured_announcements` | `announcement_structured_hot` |
| 药品审批 | `drug_approvals` | `drug_approval_hot` |
| 临床试验 | `clinical_trials` | `clinical_trial_event_hot` |
| 集中采购 | `procurement_events` | `centralized_procurement_event_hot` |
| 监管风险 | `regulatory_risks` | `regulatory_risk_event_hot` |

### 5.4 news-package → `/api/ingest/news-package`

| 数据类别 | ingest 字段 | 目标表 |
|----------|-------------|--------|
| 宏观指标 | `macro_indicators` | `macro_indicator_hot` |
| 新闻原文 | `news_raw` | `news_raw_hot` |
| 结构化新闻 | `news_structured` | `news_structured_hot` |
| 新闻-行业映射 | `news_industry_maps` | `news_industry_map_hot` |
| 新闻-公司映射 | `news_company_maps` | `news_company_map_hot` |
| 行业影响事件 | `industry_impact_events` | `industry_impact_event_hot` |

**配置源文件**：`backend/crawler/configs/table_mapping.yaml`

---

## 6. 专利数据 Schema Gap 说明

### 6.1 现状

- **现有表结构**：在 `app/core/database/models/` 全部 ORM 文件中检索，**不存在任何与 patent 相关的表**。
- **现有 ingest 接口**：`IngestCompanyPackageModel`、`IngestFinancialPackageModel`、`IngestAnnouncementPackageModel`、`IngestNewsPackageModel` 四个 schema 中，**均未定义专利相关字段**。
- **现有 service / repository**：无任何 `PatentService`、`PatentWriteService`、`PatentRepository` 或类似模块。

### 6.2 Gap 明细

| 缺失项 | 说明 |
|--------|------|
| ORM Model | 需要新增 `PatentHot` 或类似模型 |
| DB Table | 需要新增 `patent_hot` 表 |
| Ingest Schema | 需要四个 package 之一（或新 package）支持专利字段 |
| Write Service | 需要 `PatentWriteService` + `PatentWriteRepository` |
| Ingest Gateway | 需要 `IngestGatewayService` 新增专利入口方法 |

### 6.3 当前处理策略

- 配置层已注册 `patent` 数据类别（见 `table_mapping.yaml`）。
- 采集脚本可先按 `raw/patents/cnipa_patents.json` 落盘。
- **暂不入库**，待后续 Phase 完成数据库 schema 扩展与 ingest 接口扩展后再接入主链路。

---

## 7. 配置加载工具

`backend/crawler/configs/__init__.py` 提供以下工具函数，供 scripts / pipelines 使用：

- `get_stock_codes()` → 返回 10 家固定股票代码列表
- `get_companies()` → 返回公司详细信息列表
- `get_window_days(data_category)` → 返回某类数据的时间窗口
- `get_mapping(data_category)` → 返回某类数据的完整映射（含 ingest_package、target_table、raw_path 等）
- `list_data_categories()` → 返回所有已注册数据类别
- `list_schema_gaps()` → 返回当前存在 schema gap 的数据类别

**使用示例**：

```python
from crawler.configs import get_stock_codes, get_window_days, get_mapping

codes = get_stock_codes()                    # ['600276', '300122', ...]
days = get_window_days("announcement")       # 30
mapping = get_mapping("financial_note")      # {ingest_package: 'financial-package', ...}
```

---

## 8. 变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-04-23 | Phase 1 初始化：固定 10 家公司、时间窗口、来源目录、表映射、专利 schema gap 标注 |
