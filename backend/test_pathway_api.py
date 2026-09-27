"""碳中和路径模拟接口测试（分段模型）。

前置：backend 服务已启动且 energy_records 已有种子数据。
运行：python test_pathway_api.py
"""
import os

import requests

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    tok = requests.post(f"{BASE}/api/auth/login", json={"username": "李老师", "password": "123456"}).json()["access_token"]
    stok = requests.post(f"{BASE}/api/auth/login", json={"username": "张三", "password": "123456"}).json()["access_token"]

    # 1 鉴权
    r = requests.get(f"{BASE}/api/pathway/simulate")
    print("1 no token:", r.status_code)
    assert r.status_code == 401
    r = requests.get(f"{BASE}/api/pathway/simulate", headers=h(stok))
    print("1 student:", r.status_code)
    assert r.status_code == 403

    # 2 结构与基线
    d = requests.get(f"{BASE}/api/pathway/simulate", headers=h(tok)).json()
    base = d["base_emission_t"]
    print("2 base:", d["base_year"], base, "t |", len(d["scenarios"]), "scenarios | conclusion:", d["conclusion"][:20], "...")
    assert base > 0 and len(d["scenarios"]) == 3
    assert "双碳目标" in d["conclusion"]

    by_key = {s["key"]: s for s in d["scenarios"]}
    bl, eff, solar = by_key["baseline"], by_key["efficiency"], by_key["solar"]
    assert {s["tag"] for s in d["scenarios"]} == {"保守", "现实推荐", "理想激进"}

    # 3 基准·保守：2030 达峰 = base×1.015^4，平台期不变，无法中和
    exp_peak = round(base * 1.015 ** 4, 2)
    print("3 保守:", bl["peak_year"], bl["peak_emission_t"], "| 2060:", bl["emission_2060_t"], "|", bl["neutral_note"])
    assert bl["peak_year"] == 2030 and bl["peak_emission_t"] == exp_peak
    assert bl["neutral_year"] is None and bl["emission_2060_t"] == exp_peak and "无法" in bl["neutral_note"]

    # 4 节能改造·现实推荐：2028 达峰 = base×1.015×1.005，年减排 = 峰值/32，2060 归零
    exp_peak_e = round(base * 1.015 * 1.005, 2)
    print("4 节能:", eff["peak_year"], eff["peak_emission_t"], "| 年减排", eff["annual_decline_t"], "|", eff["neutral_note"])
    assert eff["peak_year"] == 2028 and eff["peak_emission_t"] == exp_peak_e
    assert eff["annual_decline_t"] == round(exp_peak_e / 32, 2)
    assert eff["neutral_year"] == 2060 and eff["emission_2060_t"] == 0.0
    got_2027 = next(p["emission_t"] for p in eff["series"] if p["year"] == 2027)
    assert got_2027 == round(base * 1.015, 2)  # 2027 仅 +1.5%

    # 5 全面光伏·理想激进：2026 即达峰 = base，年减排 = base/20，2046 归零
    print("5 光伏:", solar["peak_year"], solar["peak_emission_t"], "| 年减排", solar["annual_decline_t"], "|", solar["neutral_note"])
    assert solar["peak_year"] == 2026 and solar["peak_emission_t"] == base
    assert solar["annual_decline_t"] == round(base / 20, 2)
    assert solar["neutral_year"] == 2046 and "提前 14 年" in solar["neutral_note"]
    got_2046 = next(p["emission_t"] for p in solar["series"] if p["year"] == 2046)
    assert got_2046 == 0.0

    # 6 序列形状：35 年；最大值 = 峰值排放；达峰后单调不增；终值 = 2060 排放
    for s in d["scenarios"]:
        vals = [p["emission_t"] for p in s["series"]]
        peak_i = vals.index(s["peak_emission_t"])
        assert len(vals) == 35 and vals[0] == base
        assert max(vals) == s["peak_emission_t"]
        assert all(a >= b for a, b in zip(vals[peak_i:], vals[peak_i + 1:])), s["name"]
        assert vals[-1] == s["emission_2060_t"]
    print("6 series: 35 年、峰值与达峰后单调性 ✓")

    print("\nALL PATHWAY CHECKS PASSED")


if __name__ == "__main__":
    main()
