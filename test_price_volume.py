"""
量价分析工具测试脚本
运行方式：在项目根目录执行  python test_price_volume.py
（运行前请先执行 python seed_data.py 以确保日行情数据已写入）
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("APP_ENV", "production")


def pprint(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 1: 验证日行情数据已写入
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 1 — 验证日行情种子数据")
import os
os.chdir(os.path.join(os.path.dirname(__file__), "backend"))
from app.core.database.session import SessionLocal
from app.core.database.models.financial_hot import FinancialHot

db = SessionLocal()
try:
    counts = {}
    for sc in ["600276", "300760", "002007", "600196"]:
        n = db.query(FinancialHot).filter_by(stock_code=sc, report_type="daily").count()
        counts[sc] = n
finally:
    db.close()

print(f"  各公司日行情记录数: {counts}")
for sc, n in counts.items():
    assert n >= 100, f"[FAIL] {sc} 只有 {n} 条日行情，预期 >=100"
print("[PASS] 日行情数据充足")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: get_price_volume_data 基本功能
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 2 — get_price_volume_data: 恒瑞医药 60日")
from agent.tools.price_volume_tools import get_price_volume_data

raw = get_price_volume_data("600276", days=60)
pprint({k: v for k, v in raw.items() if k not in ("close_prices", "volumes", "trade_dates", "open_prices", "high_prices", "low_prices", "amounts", "change_pcts")})
print(f"  首条日期: {raw['trade_dates'][0]}  末条日期: {raw['trade_dates'][-1]}")
print(f"  收盘价范围: {min(raw['close_prices']):.2f} ~ {max(raw['close_prices']):.2f}")

assert "error" not in raw, f"[FAIL] {raw.get('error')}"
assert raw["count"] >= 50, f"[FAIL] 只返回 {raw['count']} 条，预期>=50"
assert len(raw["close_prices"]) == raw["count"]
assert raw["latest"]["close"] > 0
print(f"\n[PASS] 原始行情序列获取正常，共 {raw['count']} 条")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: get_price_volume_analysis 指标计算
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 3 — get_price_volume_analysis: 恒瑞医药 60日")
from agent.tools.price_volume_tools import get_price_volume_analysis

ana = get_price_volume_analysis("600276", days=60)
pprint({k: v for k, v in ana.items() if k != "signals"})

assert "error" not in ana, f"[FAIL] {ana.get('error')}"
assert ana["price_trend"]["ma5"] is not None, "[FAIL] MA5 为 None"
assert ana["price_trend"]["ma20"] is not None, "[FAIL] MA20 为 None"
assert ana["volume_trend"]["vol_ma10"] is not None, "[FAIL] 量MA10 为 None"
assert "pearson_20d" in ana["correlation"]

pt = ana["price_trend"]
vt = ana["volume_trend"]
print(f"\n  MA5={pt['ma5']}  MA10={pt['ma10']}  MA20={pt['ma20']}")
print(f"  MA20偏离={pt['ma20_deviation']}  动量5d={pt['momentum_5d']}  动量20d={pt['momentum_20d']}")
print(f"  量MA10={vt['vol_ma10']}  量比={vt['vol_ratio_latest']}")
print(f"  量价相关: {ana['correlation']['pearson_20d']}  ({ana['correlation']['interpretation']})")
print(f"  振幅均值: {ana['amplitude']['pct']}")
print(f"  量价信号总数: {ana['signal_stats']['total']}  (放量上涨:{ana['signal_stats']['放量上涨']}  放量下跌:{ana['signal_stats']['放量下跌']})")
print(f"\n  综合判断: {ana['summary']}")
print(f"\n[PASS] 量价指标计算完成")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 4: 信号检测详情
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 4 — 量价信号详情（最近10条）")
signals = ana.get("signals", [])
if signals:
    for s in signals[:5]:
        print(f"  [{s['date']}] {s['type']}  涨跌:{s['change_pct']:.2f}%  量比:{s['volume_ratio']}x")
        print(f"    {s['detail']}")
    print(f"\n  共 {len(signals)} 条信号（展示前5条）")
    print("[PASS] 信号检测正常")
else:
    print("  [INFO] 当前数据窗口内无显著量价信号（正常，取决于随机数据）")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 5: get_price_volume_event_correlation
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 5 — get_price_volume_event_correlation: 迈瑞医疗 120日")
from agent.tools.price_volume_tools import get_price_volume_event_correlation

corr = get_price_volume_event_correlation("300760", days=120)
pprint({k: v for k, v in corr.items() if k != "anomalies"})

assert "error" not in corr, f"[FAIL] {corr.get('error')}"
print(f"\n  分析天数: {corr['days_analyzed']}  异动次数: {corr['anomaly_count']}")
if corr["anomalies"]:
    for a in corr["anomalies"][:3]:
        print(f"\n  [{a['date']}] {a['type']}  涨跌:{a['price_change_pct']:.2f}%  量比:{a['volume_ratio']}x")
        print(f"    相关事件: {len(a['nearby_events'])} 条")
        print(f"    解读: {a['interpretation']}")
print(f"\n  汇总: {corr['summary']}")
print(f"\n[PASS] 量价事件关联分析完成")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 6: 多公司量价对比（同时分析4家，比较动量）
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 6 — 多公司量价对比")
companies = [("600276", "恒瑞医药"), ("300760", "迈瑞医疗"), ("002007", "华兰生物"), ("600196", "复星医药")]
results = []
for sc, name in companies:
    r = get_price_volume_analysis(sc, days=60)
    if "error" not in r:
        results.append({
            "name": name,
            "code": sc,
            "momentum_20d": r["price_trend"]["momentum_20d"],
            "vol_ratio": r["volume_trend"]["vol_ratio_latest"],
            "corr": r["correlation"]["pearson_20d"],
            "bull_signals": r["signal_stats"]["放量上涨"],
            "summary": r["summary"][:30],
        })

results.sort(key=lambda x: (x["momentum_20d"] or -999), reverse=True)
print("\n  近20日价格动量排名:")
for i, r in enumerate(results, 1):
    mom = f"{r['momentum_20d']*100:.1f}%" if r["momentum_20d"] is not None else "N/A"
    print(f"  #{i} {r['name']}({r['code']})  动量={mom}  量比={r['vol_ratio']}  量价相关={r['corr']}")
print("[PASS] 多公司对比完成")


print("\n" + "=" * 60)
print("  所有测试完成")
print("=" * 60)
