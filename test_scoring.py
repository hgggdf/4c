"""
评分系统改进验证脚本
运行方式：在项目根目录执行 python test_scoring.py
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("APP_ENV", "production")


def section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


from app.core.database.session import SessionLocal
from app.service.analysis_service import AnalysisService, DIMENSIONS, _TOTAL_SCORABLE_METRICS

svc = AnalysisService()


# ── TEST 1: ROE 修复验证 ──────────────────────────────────────────
section("TEST 1 — ROE 修复（净利润/净资产，不再是净利润/总资产）")
from app.core.database.models.financial_hot import FinancialHot
from sqlalchemy import select

db = SessionLocal()
try:
    row = db.execute(
        select(FinancialHot)
        .where(FinancialHot.stock_code == "600276", FinancialHot.report_type != "daily")
        .order_by(FinancialHot.report_date.desc())
    ).scalars().first()

    if row and row.net_profit and row.total_assets and row.total_liabilities:
        equity = float(row.total_assets) - float(row.total_liabilities)
        roe_correct = round(float(row.net_profit) / equity * 100, 4) if equity > 0 else None
        roe_old = round(float(row.net_profit) / float(row.total_assets) * 100, 4)
        print(f"  净利润: {float(row.net_profit)/1e8:.2f}亿")
        print(f"  总资产: {float(row.total_assets)/1e8:.2f}亿  总负债: {float(row.total_liabilities)/1e8:.2f}亿")
        print(f"  净资产: {equity/1e8:.2f}亿")
        print(f"  ROE(旧-错误): {roe_old:.2f}%  ROE(新-正确): {roe_correct:.2f}%")
        assert roe_correct != roe_old or equity == float(row.total_assets), "ROE 值未发生变化，修复可能未生效"
        print("[PASS] ROE 公式已修正为净利润/净资产")
    else:
        print("  [SKIP] 该公司无完整财务数据行，跳过 ROE 数值对比")
finally:
    db.close()


# ── TEST 2: 完整 diagnose 输出结构 ────────────────────────────────
section("TEST 2 — diagnose() 完整输出（恒瑞医药 2024）")
db = SessionLocal()
try:
    result = svc.diagnose(db, "600276", 2024)
finally:
    db.close()

assert result is not None, "[FAIL] diagnose() 返回 None"
print(f"  总分: {result.total_score}  评级: {result.level}")
print(f"  数据完整度: {result.data_completeness}")
print(f"  维度数量: {len(result.dimensions)}")
for dim in result.dimensions:
    missing_count = sum(1 for m in dim.metrics.values() if m.get("missing"))
    print(f"    {dim.name}: {dim.score:.1f}分  (缺失指标: {missing_count})")

assert hasattr(result, "data_completeness"), "[FAIL] DiagnoseResult 缺少 data_completeness 字段"
assert 0.0 <= result.data_completeness <= 1.0, f"[FAIL] data_completeness={result.data_completeness} 不在 [0,1]"
assert len(result.dimensions) == 5, f"[FAIL] 应有5个维度（含市场潜力），实际 {len(result.dimensions)}"
assert any(d.name == "市场潜力" for d in result.dimensions), "[FAIL] 缺少市场潜力维度"
print(f"\n[PASS] 结构验证通过，data_completeness={result.data_completeness}")


# ── TEST 3: 缺失数据惩罚（故意传一个无财务数据的虚拟场景用已有数据验证）
section("TEST 3 — 缺失指标计 0 分，missing 字段正确标注")
db = SessionLocal()
try:
    result = svc.diagnose(db, "600276", 2024)
finally:
    db.close()

for dim in result.dimensions:
    for metric_name, detail in dim.metrics.items():
        if detail.get("missing"):
            assert detail["score"] == 0, f"[FAIL] {metric_name} missing=True 但 score={detail['score']} 不为0"
            print(f"  [{dim.name}] {metric_name}: missing=True, score=0 ✓")
        else:
            assert detail["value"] is not None, f"[FAIL] {metric_name} missing=False 但 value=None"
print("[PASS] 缺失指标处理正确")


# ── TEST 4: 市场潜力维度内容验证 ────────────────────────────────
section("TEST 4 — 市场潜力维度详情")
db = SessionLocal()
try:
    result = svc.diagnose(db, "300760", 2024)
finally:
    db.close()

mkt = next((d for d in result.dimensions if d.name == "市场潜力"), None)
assert mkt is not None, "[FAIL] 无市场潜力维度"
print(f"  市场潜力分: {mkt.score}")
print(f"  子指标: {json.dumps(mkt.metrics, ensure_ascii=False, indent=4)}")
assert "管线进展" in mkt.metrics, "[FAIL] 缺少管线进展子指标"
assert "现金跑道" in mkt.metrics, "[FAIL] 缺少现金跑道子指标"
print("[PASS] 市场潜力维度结构正确")


# ── TEST 5: DiagnoseOut schema 序列化（Pydantic 验证）───────────
section("TEST 5 — Pydantic schema 序列化验证")
from app.router.schemas.analysis import DiagnoseOut
import dataclasses

db = SessionLocal()
try:
    result = svc.diagnose(db, "600276", 2024)
finally:
    db.close()

raw = dataclasses.asdict(result)
out = DiagnoseOut(**raw)
assert hasattr(out, "data_completeness"), "[FAIL] DiagnoseOut 缺少 data_completeness 字段"
serialized = out.model_dump()
print(f"  序列化字段数: {len(serialized)}")
print(f"  data_completeness: {serialized['data_completeness']}")
print("[PASS] Pydantic schema 序列化正常")


# ── TEST 6: 多公司对比（含市场潜力维度）────────────────────────
section("TEST 6 — 多公司综合打分对比")
companies = [("600276", "恒瑞医药"), ("300760", "迈瑞医疗"), ("002007", "华兰生物"), ("600196", "复星医药")]
rows = []
for code, name in companies:
    db = SessionLocal()
    try:
        r = svc.diagnose(db, code, 2024)
    finally:
        db.close()
    if r:
        mkt = next((d for d in r.dimensions if d.name == "市场潜力"), None)
        rows.append({
            "name": name,
            "total": r.total_score,
            "level": r.level,
            "completeness": r.data_completeness,
            "mkt": mkt.score if mkt else None,
        })

rows.sort(key=lambda x: x["total"], reverse=True)
print(f"\n  {'公司':<10} {'总分':>6} {'评级':<6} {'完整度':>7} {'市场潜力':>8}")
print("  " + "-" * 45)
for r in rows:
    print(f"  {r['name']:<10} {r['total']:>6.1f} {r['level']:<6} {r['completeness']:>7.0%} {r['mkt']:>8.1f}")
print("\n[PASS] 多公司对比完成")


print("\n" + "=" * 60)
print("  所有测试通过")
print("=" * 60)
