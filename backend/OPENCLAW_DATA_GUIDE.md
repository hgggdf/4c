# OpenClaw 数据投递与自动入库说明

## 一、整体流程

```
OpenClaw 爬虫
    │
    │  生成 envelope JSON 文件
    ▼
ingest_center/openclaw_inbox/     ← 投递目录（每条数据一个文件）
    │
    │  python -m ingest_center.openclaw_adapter
    ▼
MySQL 数据库                       ← 自动入库，成功后删除源文件
    │
    ▼
ingest_center/manifests_openclaw/ ← 入库凭证（manifest + receipt）
```

---

## 二、投递目录

OpenClaw 爬虫把生成的 JSON 文件放到这个目录：

```
backend/ingest_center/openclaw_inbox/
```

- 每条数据对应一个 `.json` 文件
- 文件名随意，建议格式：`{payload_type}_{stock_code}_{日期}_{序号}.json`
- 入库成功后文件会被自动删除

---

## 三、文件格式：统一 Envelope 结构

每个 JSON 文件都是一个 envelope，顶层结构固定：

```json
{
  "batch_id": "20260425_001",
  "task_id": "任意字符串，标识本次爬取任务",
  "source": {
    "source_type": "数据来源类型，如 cninfo / eastmoney / wind",
    "source_name": "来源名称",
    "source_url": "原始页面 URL",
    "source_category": "数据分类"
  },
  "entity": {
    "entity_type": "company",
    "stock_code": "600276",
    "stock_name": "恒瑞医药",
    "industry_code": "IND_MED_01",
    "industry_name": "医药制造"
  },
  "document": {
    "doc_type": "html / pdf / json",
    "title": "文档标题",
    "publish_time": "2026-04-25T00:00:00+08:00",
    "crawl_time": "2026-04-25T10:00:00+08:00",
    "file_hash": "文件内容的 MD5 或 SHA256，用于去重",
    "raw_file_path": "爬虫原始文件路径（可选）",
    "language": "zh"
  },
  "payload_type": "见下方14种",
  "payload": { ... },
  "processing": {
    "parse_status": "parsed",
    "parse_method": "llm / rule / manual",
    "confidence_score": 1.0,
    "version_no": "v1"
  },
  "extra": {}
}
```

**注意：** `batch_id`、`payload_type`、`payload`、`source`、`entity`、`document` 为必填字段。

---

## 四、14 种 payload_type 详细格式

### 1. `company_profile` — 公司概况

```json
{
  "batch_id": "20260425_001",
  "task_id": "crawl_company_600276",
  "source": {
    "source_type": "cninfo",
    "source_url": "https://www.cninfo.com.cn/..."
  },
  "entity": {
    "stock_code": "600276",
    "stock_name": "恒瑞医药",
    "industry_code": "IND_MED_01",
    "industry_name": "医药制造"
  },
  "document": { "title": "公司概况", "publish_time": "2026-04-25T00:00:00+08:00" },
  "payload_type": "company_profile",
  "payload": {
    "business_summary": "公司主营业务描述文本",
    "core_products_json": ["注射用紫杉醇", "阿帕替尼"],
    "main_segments_json": ["肿瘤", "心血管", "代谢"],
    "market_position": "国内抗肿瘤药龙头",
    "management_summary": "管理层介绍文本"
  },
  "processing": { "parse_status": "parsed", "confidence_score": 1.0 },
  "extra": {}
}
```

**入库结果：** 写入 `company_master` + `company_profile` 两张表。

---

### 2. `announcement_raw` — 公告原始数据

```json
{
  "payload_type": "announcement_raw",
  "entity": { "stock_code": "600276" },
  "document": {
    "title": "2025年年度报告",
    "publish_time": "2026-04-20T00:00:00+08:00",
    "file_hash": "abc123def456"
  },
  "source": { "source_type": "cninfo", "source_url": "https://..." },
  "payload": {
    "announcement_type": "年度报告",
    "exchange": "SSE",
    "content": "公告正文全文..."
  },
  "extra": {}
}
```

**入库结果：** 写入 `announcement_raw_hot` 表，返回数据库 `id`。

---

### 3. `announcement_structured` — 公告结构化数据

> ⚠️ **必须先入库对应的 `announcement_raw`**，拿到返回的数据库 `id` 填入 `extra.announcement_id`。

```json
{
  "payload_type": "announcement_structured",
  "entity": { "stock_code": "600276" },
  "document": { "title": "2025年年度报告" },
  "source": { "source_type": "cninfo" },
  "payload": {
    "category": "业绩报告",
    "summary_text": "公司2025年实现营收270亿元，同比增长15%",
    "key_fields_json": { "营收": "270亿", "净利润": "60亿", "同比增速": "15%" },
    "signal_type": "positive",
    "risk_level": "low"
  },
  "extra": {
    "announcement_id": 123
  }
}
```

**入库结果：** 写入 `announcement_structured_hot` 表。

---

### 4. `news_raw` — 新闻原始数据

```json
{
  "payload_type": "news_raw",
  "entity": {},
  "document": {
    "title": "恒瑞医药新药获批上市",
    "publish_time": "2026-04-25T08:00:00+08:00",
    "file_hash": "news_hash_001",
    "language": "zh"
  },
  "source": {
    "source_type": "eastmoney",
    "source_name": "东方财富",
    "source_url": "https://..."
  },
  "payload": {
    "news_uid": "eastmoney_20260425_001",
    "author_name": "记者姓名",
    "content": "新闻正文全文...",
    "news_type": "company"
  },
  "extra": {}
}
```

**注意：** `news_uid` 是全局唯一标识，用于去重，必填。

---

### 5. `news_structured` — 新闻结构化数据

```json
{
  "payload_type": "news_structured",
  "entity": {},
  "document": { "title": "恒瑞医药新药获批上市" },
  "source": { "source_type": "eastmoney" },
  "payload": {
    "topic_category": "drug_approval",
    "summary_text": "恒瑞医药某创新药获NMPA批准上市",
    "keywords_json": ["创新药", "获批", "恒瑞医药"],
    "signal_type": "positive",
    "impact_level": "high",
    "impact_horizon": "medium",
    "sentiment_label": "positive",
    "confidence_score": 0.95
  },
  "extra": {}
}
```

---

### 6. `financial_statement` — 财务报表

`statement_type` 三选一：`income_statement` / `balance_sheet` / `cashflow_statement`

**利润表：**
```json
{
  "payload_type": "financial_statement",
  "entity": { "stock_code": "600276" },
  "source": { "source_type": "wind" },
  "payload": {
    "statement_type": "income_statement",
    "report_date": "2025-12-31",
    "revenue": 27000000000,
    "operating_cost": 5000000000,
    "gross_profit": 22000000000,
    "selling_expense": 8000000000,
    "admin_expense": 1500000000,
    "rd_expense": 6000000000,
    "operating_profit": 7000000000,
    "net_profit": 6000000000,
    "net_profit_deducted": 5800000000,
    "eps": 2.5
  },
  "extra": { "fiscal_year": 2025, "report_type": "annual" }
}
```

**资产负债表：**
```json
{
  "payload_type": "financial_statement",
  "payload": {
    "statement_type": "balance_sheet",
    "report_date": "2025-12-31",
    "total_assets": 50000000000,
    "total_liabilities": 15000000000,
    "accounts_receivable": 3000000000,
    "inventory": 2000000000,
    "cash": 20000000000,
    "equity": 35000000000,
    "goodwill": 500000000
  },
  "extra": { "fiscal_year": 2025, "report_type": "annual" }
}
```

**现金流量表：**
```json
{
  "payload_type": "financial_statement",
  "payload": {
    "statement_type": "cashflow_statement",
    "report_date": "2025-12-31",
    "operating_cashflow": 7500000000,
    "investing_cashflow": -3000000000,
    "financing_cashflow": -1000000000,
    "free_cashflow": 4500000000
  },
  "extra": { "fiscal_year": 2025, "report_type": "annual" }
}
```

---

### 7. `financial_metric` — 财务指标

```json
{
  "payload_type": "financial_metric",
  "entity": { "stock_code": "600276" },
  "payload": {
    "report_date": "2025-12-31",
    "fiscal_year": 2025,
    "metric_name": "ROE",
    "metric_value": 0.18,
    "metric_unit": "%",
    "calc_method": "standard"
  },
  "extra": {}
}
```

---

### 8. `macro_indicator` — 宏观指标

```json
{
  "payload_type": "macro_indicator",
  "entity": {},
  "source": { "source_type": "NBS", "source_url": "https://www.stats.gov.cn/..." },
  "payload": {
    "indicator_name": "CPI",
    "period": "2026-03",
    "value": 0.5,
    "unit": "%"
  },
  "extra": {}
}
```

---

### 9. `drug_event` — 药品审批事件

目前 `event_kind` 只支持 `drug_approval`。

```json
{
  "payload_type": "drug_event",
  "entity": { "stock_code": "600276" },
  "source": { "source_type": "NMPA", "source_url": "https://..." },
  "payload": {
    "event_kind": "drug_approval",
    "drug_name": "注射用SHR-1210",
    "approval_type": "NDA",
    "approval_date": "2026-04-01",
    "indication": "非小细胞肺癌",
    "drug_stage": "approved",
    "is_innovative_drug": 1,
    "review_status": "approved",
    "market_scope": "China"
  },
  "extra": { "source_announcement_id": null }
}
```

---

### 10. `procurement_event` — 集采事件

```json
{
  "payload_type": "procurement_event",
  "entity": { "stock_code": "600276" },
  "source": { "source_type": "NHSA" },
  "payload": {
    "drug_name": "注射用紫杉醇",
    "procurement_round": "第九批",
    "bid_result": "won",
    "price_change_ratio": -0.32,
    "event_date": "2026-04-01",
    "impact_summary": "中标，降价32%，预计影响收入约5亿元"
  },
  "extra": { "source_announcement_id": null }
}
```

---

### 11. `trial_event` — 临床试验事件

```json
{
  "payload_type": "trial_event",
  "entity": { "stock_code": "600276" },
  "source": { "source_type": "CDE" },
  "payload": {
    "drug_name": "SHR-1210",
    "trial_phase": "Phase3",
    "event_type": "enrollment_complete",
    "event_date": "2026-04-01",
    "indication": "非小细胞肺癌",
    "summary_text": "三期临床试验完成入组，共纳入患者600例"
  },
  "extra": { "source_announcement_id": null }
}
```

---

### 12. `regulatory_risk_event` — 监管风险事件

```json
{
  "payload_type": "regulatory_risk_event",
  "entity": { "stock_code": "600276" },
  "source": { "source_type": "NMPA" },
  "payload": {
    "risk_type": "inspection",
    "event_date": "2026-04-01",
    "risk_level": "medium",
    "summary_text": "收到NMPA飞行检查通知，涉及某生产线GMP合规性"
  },
  "extra": { "source_announcement_id": null }
}
```

---

### 13. `stock_daily` — 股票日行情

```json
{
  "payload_type": "stock_daily",
  "entity": { "stock_code": "600276" },
  "source": { "source_type": "tushare" },
  "payload": {
    "trade_date": "2026-04-25",
    "open_price": 50.20,
    "close_price": 51.80,
    "high_price": 52.50,
    "low_price": 49.90,
    "volume": 12500000,
    "turnover": 647500000
  },
  "extra": {}
}
```

---

### 14. `news_company_map` — 新闻公司关联

```json
{
  "payload_type": "news_company_map",
  "entity": { "stock_code": "600276" },
  "source": { "source_type": "eastmoney" },
  "payload": {
    "news_uid": "eastmoney_20260425_001",
    "relevance_score": 0.95,
    "mention_type": "primary"
  },
  "extra": {}
}
```

---

## 五、调用入库的命令

### 方式一：命令行（推荐）

在 `backend/` 目录下执行：

```bash
# 处理 openclaw_inbox/ 下所有文件
python -m ingest_center.openclaw_adapter

# 只处理某种类型
python -m ingest_center.openclaw_adapter --payload-type announcement_raw

# 预演模式（只校验不入库）
python -m ingest_center.openclaw_adapter --dry-run

# 指定自定义目录
python -m ingest_center.openclaw_adapter --inbox-dir /path/to/your/inbox
```

### 方式二：Python 代码调用

```python
import sys, os
os.environ['TRANSFORMERS_OFFLINE'] = '1'
sys.path.insert(0, 'backend/')  # 根据实际路径调整

from ingest_center.openclaw_adapter import run

result = run()
print(result)  # {"success": True, "results": [...]}
```

### 方式三：HTTP API（服务运行时）

服务启动后，也可以直接 POST 单条 envelope：

```
POST http://127.0.0.1:8000/api/openclaw/ingest
Content-Type: application/json

{ ...envelope JSON... }
```

---

## 六、入库流程说明

1. 扫描 `openclaw_inbox/` 下所有 `.json` 文件
2. 校验 envelope 顶层结构（缺字段或 payload_type 不合法会跳过）
3. 按 `payload_type` 分组批量入库（同类型合并一次调用）
4. 入库成功 → 删除源文件，生成 manifest 到 `manifests_openclaw/`
5. 无论成功失败 → 生成 receipt 到 `receipts/`

---

## 七、注意事项

| 事项 | 说明 |
|------|------|
| `announcement_structured` 的依赖 | 必须先入库对应的 `announcement_raw`，把返回的 `id` 填入 `extra.announcement_id` |
| `news_uid` 唯一性 | `news_raw` 的 `news_uid` 全局唯一，重复投递会更新而不是新增 |
| `file_hash` 去重 | `announcement_raw` 按 `file_hash` 去重，同一文件重复投递不会产生重复记录 |
| 金额单位 | 财务数据统一用**元**（不是万元或亿元） |
| 时间格式 | 统一用 ISO 8601：`2026-04-25T00:00:00+08:00` |
| `extra` 字段 | 不需要时传空对象 `{}`，不能省略 |
| 服务启动参数 | 启动服务时加 `TRANSFORMERS_OFFLINE=1` 避免 HuggingFace 网络超时 |
