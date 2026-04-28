# OpenClaw 爬取与入库对接指南

## 一、总体流程

```
OpenClaw 爬取数据
      ↓
按规范生成 JSONL + 原始文件
      ↓
放入 data/incoming/{batch_id}/
      ↓
执行一键入库脚本 import_batch.py
      ↓
数据写入 MySQL 正式表
```

OpenClaw 只负责爬取和输出标准数据包，不直接写数据库。

---

## 二、需要爬取的 6 类数据

| 序号 | 数据类型 | 目标表 | 唯一键 |
|------|---------|--------|--------|
| 1 | 公司基础信息 | `company` | `stock_code` |
| 2 | 财务数据 | `financial_hot` | `stock_code + report_date + report_type` |
| 3 | 公告 | `announcement_hot` | `stock_code + title + publish_date` |
| 4 | 研报 | `research_report_hot` | `report_uid` |
| 5 | 新闻 | `news_hot` | `news_uid` |
| 6 | 宏观指标 | `macro_indicator` | `indicator_name + period` |

---

## 三、数据包目录结构

每次爬取生成一个批次目录：

```
data/incoming/{batch_id}/
├── manifest.json                          # 批次描述文件（必须）
├── company/
│   └── company_records.jsonl
├── financial/
│   ├── financial_records.jsonl
│   └── files/
│       └── 600276_2024_annual.pdf
├── announcement/
│   ├── announcement_records.jsonl
│   └── files/
│       └── 600276_20240520_notice.pdf
├── research_report/
│   ├── research_report_records.jsonl
│   └── files/
│       └── company_600276_20240601.pdf
├── news/
│   ├── news_records.jsonl
│   └── files/
│       └── news_a1b2c3.html
└── macro/
    └── macro_records.jsonl
```

`batch_id` 命名格式：`{范围}_{yyyyMMdd}_{序号}`，例如 `all_20260426_001`。

---

## 四、manifest.json 格式

```json
{
  "batch_id": "all_20260426_001",
  "crawler": "openclaw",
  "created_at": "2026-04-26 15:30:00",
  "status": "ready",
  "data_types": ["company", "financial", "announcement", "research_report", "news", "macro"],
  "total_count": 520,
  "files": {
    "company": "company/company_records.jsonl",
    "financial": "financial/financial_records.jsonl",
    "announcement": "announcement/announcement_records.jsonl",
    "research_report": "research_report/research_report_records.jsonl",
    "news": "news/news_records.jsonl",
    "macro": "macro/macro_records.jsonl"
  },
  "file_encoding": "utf-8",
  "record_format": "jsonl"
}
```

`status` 必须为 `ready` 才会被入库脚本处理。不需要的数据类型可以从 `data_types` 和 `files` 中省略。

---

## 五、各类数据 JSONL 字段规范

所有 JSONL 文件要求：一行一条 JSON，UTF-8 编码，空字段用 `null`。

### 5.1 公司基础信息 — `company/company_records.jsonl`

```json
{
  "stock_code": "600276",
  "stock_name": "恒瑞医药",
  "full_name": "江苏恒瑞医药股份有限公司",
  "exchange": "SH",
  "industry_level1": "医药生物",
  "industry_code": "innovative_drug",
  "industry_level2": "创新药",
  "listing_date": "2000-10-18",
  "business_summary": "公司主要从事创新药和仿制药的研发、生产和销售……",
  "core_products_json": ["阿帕替尼", "卡瑞利珠单抗", "氟唑帕利"],
  "main_segments_json": [{"name": "创新药", "ratio": 0.65}, {"name": "仿制药", "ratio": 0.35}]
}
```

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| stock_code | 是 | string | 6位股票代码 |
| stock_name | 是 | string | 公司简称 |
| full_name | 否 | string | 公司全称 |
| exchange | 否 | string | 交易所，SH/SZ |
| industry_level1 | 否 | string | 一级行业，默认"医药生物" |
| industry_code | 否 | string | 行业代码，关联 industry_master |
| industry_level2 | 否 | string | 二级行业名称 |
| listing_date | 否 | date | 上市日期，YYYY-MM-DD |
| business_summary | 否 | string | 主营业务摘要 |
| core_products_json | 否 | array | 核心产品列表 |
| main_segments_json | 否 | array | 主营业务板块 |

### 5.2 财务数据 — `financial/financial_records.jsonl`

```json
{
  "stock_code": "600276",
  "report_date": "2024-12-31",
  "report_type": "annual",
  "revenue": 1000000000,
  "operating_cost": 400000000,
  "selling_expense": 120000000,
  "admin_expense": 50000000,
  "rd_expense": 200000000,
  "operating_profit": 300000000,
  "net_profit": 280000000,
  "net_profit_deducted": 260000000,
  "eps": 1.23,
  "total_assets": 5000000000,
  "total_liabilities": 2000000000,
  "operating_cashflow": 320000000,
  "investing_cashflow": -100000000,
  "financing_cashflow": 50000000,
  "source_url": "https://example.com/report.pdf",
  "original_filename": "恒瑞医药2024年年度报告.pdf",
  "local_file": "files/600276_2024_annual.pdf"
}
```

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| stock_code | 是 | string | 股票代码 |
| report_date | 是 | date | 报告日期，YYYY-MM-DD |
| report_type | 是 | string | annual / semiannual / q1 / q3 / daily |
| revenue | 否 | decimal | 营业收入（元） |
| operating_cost | 否 | decimal | 营业成本 |
| selling_expense | 否 | decimal | 销售费用 |
| admin_expense | 否 | decimal | 管理费用 |
| rd_expense | 否 | decimal | 研发费用 |
| operating_profit | 否 | decimal | 营业利润 |
| net_profit | 否 | decimal | 净利润 |
| net_profit_deducted | 否 | decimal | 扣非净利润 |
| eps | 否 | decimal | 每股收益 |
| total_assets | 否 | decimal | 总资产 |
| total_liabilities | 否 | decimal | 总负债 |
| operating_cashflow | 否 | decimal | 经营活动现金流 |
| investing_cashflow | 否 | decimal | 投资活动现金流 |
| financing_cashflow | 否 | decimal | 筹资活动现金流 |
| trade_date | 日行情必填 | date | 交易日期，YYYY-MM-DD |
| open_price | 日行情必填 | decimal | 开盘价（元） |
| close_price | 日行情必填 | decimal | 收盘价（元） |
| high_price | 日行情必填 | decimal | 最高价（元） |
| low_price | 日行情必填 | decimal | 最低价（元） |
| volume | 日行情必填 | decimal | 成交量（股） |
| amount | 日行情建议 | decimal | 成交额（元） |
| change_pct | 日行情建议 | decimal | 涨跌幅（%），如 3.54 表示涨 3.54% |
| source_url | 建议 | string | 财报来源链接 |
| original_filename | 有文件则必填 | string | 原始文件名 |
| local_file | 有文件则必填 | string | batch 内相对路径 |

财报记录和日行情记录共用同一个 JSONL 文件，通过 `report_type` 区分。日行情记录的 `report_type` 固定为 `daily`，`report_date` 和 `trade_date` 填同一个日期，财报字段留 `null`。

日行情数据示例：

```json
{"stock_code":"600276","report_date":"2026-04-25","report_type":"daily","trade_date":"2026-04-25","open_price":45.20,"close_price":46.80,"high_price":47.10,"low_price":44.90,"volume":12345678,"amount":576000000,"change_pct":3.54}
```

建议每只股票爬取最近 120 个交易日的日行情数据，前端 K 线图默认显示 60 天。

以下字段由入库脚本自动计算，OpenClaw 不需要提供：

- `fiscal_year` = `YEAR(report_date)`
- `gross_profit` = `revenue - operating_cost`
- `gross_margin` = `(revenue - operating_cost) / revenue`
- `rd_ratio` = `rd_expense / revenue`
- `debt_ratio` = `total_liabilities / total_assets`

### 5.3 公告 — `announcement/announcement_records.jsonl`

```json
{
  "stock_code": "600276",
  "title": "关于药品获得批准的公告",
  "publish_date": "2024-05-20",
  "announcement_type": "drug_approval",
  "content": "公告正文内容……",
  "summary_text": "公司某药品获得上市批准。",
  "key_fields_json": {
    "drug_name": "某某注射液",
    "approval_type": "上市批准",
    "indication": "肿瘤适应症"
  },
  "source_url": "https://example.com/announcement.pdf",
  "original_filename": "关于药品获得批准的公告.pdf",
  "local_file": "files/600276_20240520_notice.pdf"
}
```

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| stock_code | 是 | string | 股票代码 |
| title | 是 | string | 公告标题 |
| publish_date | 是 | date | 发布日期，YYYY-MM-DD |
| announcement_type | 否 | string | 公告类型 |
| content | 建议 | string | 公告正文 |
| summary_text | 否 | string | 公告摘要 |
| key_fields_json | 否 | object | 结构化关键信息 |
| source_url | 建议 | string | 来源链接 |
| original_filename | 有文件则必填 | string | 原始文件名 |
| local_file | 有文件则必填 | string | batch 内相对路径 |

`announcement_uid` 由入库脚本自动计算：`SHA256(stock_code + title + publish_date + file_hash)`

### 5.4 研报 — `research_report/research_report_records.jsonl`

公司研报：
```json
{
  "scope_type": "company",
  "stock_code": "600276",
  "industry_code": null,
  "title": "恒瑞医药深度研究报告",
  "publish_date": "2024-06-01",
  "report_org": "某某证券",
  "content": "研报正文内容……",
  "summary_text": "本报告认为公司创新药管线持续推进。",
  "source_type": "broker_report",
  "source_url": "https://example.com/report.pdf",
  "original_filename": "恒瑞医药深度研究报告.pdf",
  "local_file": "files/company_600276_20240601.pdf"
}
```

行业研报：
```json
{
  "scope_type": "industry",
  "stock_code": null,
  "industry_code": "innovative_drug",
  "title": "创新药行业深度报告",
  "publish_date": "2024-06-01",
  "report_org": "某某证券",
  "content": "行业研报正文……",
  "source_url": "https://example.com/industry_report.pdf",
  "original_filename": "创新药行业深度报告.pdf",
  "local_file": "files/industry_innovative_drug_20240601.pdf"
}
```

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| scope_type | 是 | string | `company` 或 `industry` |
| stock_code | 公司研报必填 | string | 股票代码 |
| industry_code | 行业研报必填 | string | 行业代码 |
| title | 是 | string | 研报标题 |
| publish_date | 建议 | date | 发布日期 |
| report_org | 否 | string | 研报机构 |
| content | 建议 | string | 研报正文 |
| summary_text | 否 | string | 研报摘要 |
| source_type | 否 | string | 来源类型 |
| source_url | 建议 | string | 来源链接 |
| original_filename | 有文件则必填 | string | 原始文件名 |
| local_file | 有文件则必填 | string | batch 内相对路径 |

`report_uid` 由入库脚本自动计算。

### 5.5 新闻 — `news/news_records.jsonl`

```json
{
  "title": "医保政策调整影响创新药行业",
  "publish_time": "2024-06-10 10:30:00",
  "source_name": "某财经网",
  "source_url": "https://example.com/news/123",
  "news_type": "policy_news",
  "content": "新闻正文内容……",
  "summary_text": "医保政策调整可能影响创新药支付环境。",
  "related_stock_codes_json": ["600276", "300347"],
  "related_industry_codes_json": ["innovative_drug"],
  "original_filename": "news_123.html",
  "local_file": "files/news_a1b2c3.html"
}
```

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| title | 是 | string | 新闻标题 |
| publish_time | 建议 | datetime | 发布时间，YYYY-MM-DD HH:MM:SS |
| source_name | 否 | string | 来源名称 |
| source_url | 建议 | string | 来源链接 |
| news_type | 否 | string | 新闻类型 |
| content | 建议 | string | 新闻正文 |
| summary_text | 否 | string | 新闻摘要 |
| related_stock_codes_json | 否 | array | 相关公司代码列表，如 `["600276"]` |
| related_industry_codes_json | 否 | array | 相关行业代码列表 |
| original_filename | 有文件则必填 | string | 原始文件名 |
| local_file | 有文件则必填 | string | batch 内相对路径 |

`news_uid` 由入库脚本自动计算：`SHA256(source_url)` 或 `SHA256(title + publish_time + source_name)`

### 5.6 宏观指标 — `macro/macro_records.jsonl`

```json
{
  "indicator_name": "医药制造业PMI",
  "period": "2024-06",
  "period_date": "2024-06-30",
  "value": 51.2,
  "unit": "%",
  "category": "行业景气度",
  "summary_text": "医药制造业PMI连续3个月位于扩张区间。",
  "source_type": "national_bureau",
  "source_url": "https://example.com/macro/pmi"
}
```

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| indicator_name | 是 | string | 指标名称 |
| period | 是 | string | 统计周期，如 `2024-06`、`2024-Q2` |
| period_date | 否 | date | 周期对应日期 |
| value | 否 | decimal | 指标值 |
| unit | 否 | string | 单位 |
| category | 否 | string | 指标类别 |
| summary_text | 否 | string | 指标说明 |
| source_type | 否 | string | 来源类型 |
| source_url | 否 | string | 来源链接 |

---

## 六、一键入库

### 6.1 入库脚本位置

```
C:\Users\17614\Desktop\4c\backend\import_batch.py
```

### 6.2 执行命令

```bash
cd C:\Users\17614\Desktop\4c\backend
python import_batch.py data/incoming/all_20260426_001
```

或批量处理所有待入库批次：

```bash
python import_batch.py --all
```

### 6.3 入库脚本功能

脚本会自动完成以下工作：

1. 读取 `manifest.json`，检查 `status == "ready"`
2. 逐类型读取 JSONL 文件
3. 校验必填字段和数据格式
4. 自动计算派生字段（`fiscal_year`、`gross_margin`、`debt_ratio` 等）
5. 自动生成唯一标识（`announcement_uid`、`report_uid`、`news_uid`）
6. 移动原始文件到 `data/raw_files/` 正式目录
7. 通过后端 API `POST /api/openclaw/ingest` 逐条写入数据库
8. 成功后将批次移动到 `data/processed/{batch_id}/`
9. 失败后将批次移动到 `data/failed/{batch_id}/` 并生成 `error_report.json`

---

## 七、入库 API 参考

后端地址：`http://127.0.0.1:8000`

统一入库接口：`POST /api/openclaw/ingest`

请求体格式（所有数据类型共用此信封）：

```json
{
  "batch_id": "all_20260426_001",
  "task_id": "task_001",
  "source": {
    "source_type": "crawler",
    "source_name": "openclaw",
    "source_url": "https://example.com/xxx"
  },
  "entity": {
    "stock_code": "600276",
    "stock_name": "恒瑞医药"
  },
  "document": {
    "title": "文档标题",
    "publish_time": "2024-05-20T00:00:00",
    "file_hash": "abc123"
  },
  "payload_type": "见下表",
  "payload": { },
  "processing": { "status": "pending" },
  "extra": { }
}
```

`payload_type` 对应关系：

| payload_type | 数据类型 | payload 内容 |
|-------------|---------|-------------|
| `company_profile` | 公司信息 | business_summary, core_products_json, main_segments_json |
| `financial_statement` | 财务数据 | statement_type + 财务字段（见 5.2） |
| `announcement_raw` | 公告 | announcement_type, content |
| `news_raw` | 新闻 | news_uid, content, news_type |
| `macro_indicator` | 宏观指标 | indicator_name, period, value, unit, category |

---

## 八、原始文件命名规范与存储位置

### 8.1 batch 内临时存放（OpenClaw 输出时）

OpenClaw 爬取的原始文件（PDF、HTML 等）放在各数据类型目录下的 `files/` 子目录中：

```
data/incoming/{batch_id}/
├── financial/files/          # 财报 PDF
├── announcement/files/       # 公告 PDF/HTML
├── research_report/files/    # 研报 PDF
├── news/files/               # 新闻 HTML
└── macro/files/              # 宏观数据 XLSX（如有）
```

JSONL 中通过 `local_file` 字段指向该文件，必须使用相对路径（相对于该数据类型目录）：

```json
{"local_file": "files/600276_2024_annual.pdf"}
```

### 8.2 文件命名规则

统一格式：`{日期}-{业务标识}-{短标题}-{hash后6位}.{后缀}`

各类型具体规则：

| 数据类型 | 命名格式 | 示例 |
|---------|---------|------|
| 财报 | `{stock_code}_{year}_{report_type}.pdf` | `600276_2024_annual.pdf` |
| 公告 | `{stock_code}_{yyyyMMdd}_{短标题}.pdf` | `600276_20240520_药品获批公告.pdf` |
| 公司研报 | `company_{stock_code}_{yyyyMMdd}.pdf` | `company_600276_20240601.pdf` |
| 行业研报 | `industry_{industry_code}_{yyyyMMdd}.pdf` | `industry_innovative_drug_20240601.pdf` |
| 新闻 | `news_{hash}.html` | `news_a1b2c3d4.html` |
| 宏观 | `macro_{year}_{类别}.xlsx` | `macro_2024_healthcare.xlsx` |

要求：
- 文件名只用英文、数字、下划线、短横线，不要空格和特殊字符
- 中文短标题可以保留，但建议控制在 10 字以内
- 同一 batch 内文件名不能重复

### 8.3 入库后正式存储位置

入库脚本会自动将 `files/` 中的文件移动到 `data/raw_files/` 正式目录：

```
data/raw_files/
├── financial/
│   └── {year}/{stock_code}/
│       └── 600276_2024_annual.pdf
│
├── announcement/
│   └── {year}/{stock_code}/
│       └── 600276_20240520_药品获批公告.pdf
│
├── research_report/
│   ├── company/{year}/{stock_code}/
│   │   └── company_600276_20240601.pdf
│   └── industry/{year}/{industry_code}/
│       └── industry_innovative_drug_20240601.pdf
│
├── news/
│   └── {year}/{month}/
│       └── news_a1b2c3d4.html
│
└── macro/
    └── {year}/
        └── macro_2024_healthcare.xlsx
```

移动完成后，数据库记录的 `file_path` 字段会更新为正式路径（如 `raw_files/financial/2024/600276/600276_2024_annual.pdf`）。

### 8.4 文件存放原则

1. 原始文件不存数据库，数据库只保存 `file_path`
2. 下载后计算 `file_hash`（SHA256），用于去重
3. 不要在新爬取前删除 `raw_files` 历史文件
4. 冷热库迁移时不移动原始文件

---

## 九、OpenClaw 不应该做的事

1. 不直接写 MySQL 数据库
2. 不写 hot / archive 表
3. 不更新 query_count
4. 不触发向量化
5. 不删除 raw_files 历史文件
6. 不修改 processed / failed 目录
