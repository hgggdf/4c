"""
估值分析工具测试脚本
运行方式：在项目根目录执行  python test_valuation.py
"""
import sys
import os
import json

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

os.environ.setdefault("APP_ENV", "production")

# ──────────────────────────────────────────────────────────────────────────────

def pprint(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def section(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ──────────────────────────────────────────────────────────────────────────────
# 测试 1: 单公司估值指标（恒瑞医药）
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 1 — get_valuation_metrics: 恒瑞医药 (600276)")
from agent.tools.valuation_tools import get_valuation_metrics

result = get_valuation_metrics("600276")
pprint(result)

# 基本断言
assert "pe" in result or "error" in result, "返回结构异常"
if "error" not in result:
    assert "summary" in result, "缺少 summary 字段"
    assert "data_period" in result, "缺少 data_period 字段"
    print("\n[PASS] 恒瑞医药估值指标计算完成")
    print(f"  PE: {result['pe']['value']}  |  PB: {result['pb']['value']}  |  PS: {result['ps']['value']}")
    print(f"  PEG: {result['peg']['value']}  |  EV/EBITDA: {result['ev_ebitda']['value']}")
    print(f"  结论: {result['summary']}")
else:
    print(f"[WARN] 数据不足: {result['error']}")


# ──────────────────────────────────────────────────────────────────────────────
# 测试 2: 传入自定义股价
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 2 — get_valuation_metrics: 迈瑞医疗 (300760) 传入股价=250")
from agent.tools.valuation_tools import get_valuation_metrics

result2 = get_valuation_metrics("300760", current_price=250.0)
pprint(result2)

if "error" not in result2:
    assert result2["price"]["value"] == 250.0, "stock price not applied"
    assert result2["price"]["source"] == "用户传入", "price source mismatch"
    print(f"\n[PASS] 传入股价正确: {result2['price']}")
    print(f"  结论: {result2['summary']}")
else:
    print(f"[WARN] 数据不足: {result2['error']}")


# ──────────────────────────────────────────────────────────────────────────────
# 测试 3: DCF 估值（恒瑞医药）
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 3 — get_dcf_valuation: 恒瑞医药 (600276)")
from agent.tools.valuation_tools import get_dcf_valuation

dcf = get_dcf_valuation("600276", wacc=0.10, terminal_growth=0.03, forecast_years=5)
pprint(dcf)

if "error" not in dcf:
    assert "total_intrinsic_value" in dcf, "缺少 total_intrinsic_value"
    assert "forecast_detail" in dcf, "缺少 forecast_detail"
    assert len(dcf["forecast_detail"]) == 5, "预测年数不符"
    print(f"\n[PASS] DCF 估值完成")
    print(f"  历史 FCF 增速: {dcf.get('fcf_growth_rate')}")
    print(f"  预测 FCF 增速: {dcf.get('forecast_growth_rate')}")
    print(f"  预测期现值之和: {dcf.get('pv_forecast')}")
    print(f"  终值现值: {dcf.get('pv_terminal')}")
    print(f"  公司内在总价值: {dcf.get('total_intrinsic_value')}")
    print(f"  每股内在价值: {dcf.get('intrinsic_value_per_share')}")
else:
    print(f"[WARN] {dcf['error']}")


# ──────────────────────────────────────────────────────────────────────────────
# 测试 4: DCF 敏感性（不同 WACC）
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 4 — DCF 敏感性分析: 恒瑞医药 WACC 8% / 10% / 12%")
for w in [0.08, 0.10, 0.12]:
    r = get_dcf_valuation("600276", wacc=w)
    if "error" not in r:
        print(f"  WACC={w*100:.0f}%  →  每股内在价值: {r.get('intrinsic_value_per_share')}元  总价值: {r.get('total_intrinsic_value')}")
    else:
        print(f"  WACC={w*100:.0f}%  →  {r['error']}")


# ──────────────────────────────────────────────────────────────────────────────
# 测试 5: 多公司横向对比
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 5 — get_valuation_comparison: 恒瑞 / 迈瑞 / 华兰 / 复星")
from agent.tools.valuation_tools import get_valuation_comparison

comp = get_valuation_comparison(["600276", "300760", "002007", "600196"])
pprint(comp)

if "ranking" in comp:
    print("\n[PASS] 横向对比完成")
    print("\n  综合吸引力排名:")
    for r in comp["ranking"]:
        print(f"    #{r['rank']} {r['stock_name']}({r['stock_code']})  PE={r.get('pe')}  PB={r.get('pb')}  PEG={r.get('peg')}  ROE={r.get('roe')}")
    print(f"\n  行业均值: PE={comp['industry_avg'].get('pe')}  PB={comp['industry_avg'].get('pb')}  ROE={comp['industry_avg'].get('roe')}")
    print(f"\n  结论: {comp['conclusion']}")
else:
    print("[WARN] 横向对比数据不足")


# ──────────────────────────────────────────────────────────────────────────────
# 测试 6: 全部8家种子公司对比
# ──────────────────────────────────────────────────────────────────────────────
section("TEST 6 — 全部种子公司估值横向对比")
all_codes = ["600276", "000858", "300760", "002007", "600196", "300347", "600085", "002252"]
comp_all = get_valuation_comparison(all_codes)

if "ranking" in comp_all:
    print("  综合吸引力排名 (全部8家):")
    for r in comp_all["ranking"]:
        print(f"    #{r['rank']} {r['stock_name']}({r['stock_code']})  PE={r.get('pe')}  PEG={r.get('peg')}")
    print(f"\n  {comp_all['conclusion']}")
else:
    print("[WARN] 数据不足")


print("\n" + "=" * 60)
print("  所有测试完成")
print("=" * 60)
