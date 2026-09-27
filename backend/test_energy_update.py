"""能耗录入修改（PUT）接口测试。

前置：backend 服务已启动且 energy_records 已有种子数据。
运行：python test_energy_update.py  （API_BASE 可覆盖服务地址）
"""
import os

import requests

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    tok = requests.post(f"{BASE}/api/auth/login", json={"username": "李老师", "password": "123456"}).json()["access_token"]
    stok = requests.post(f"{BASE}/api/auth/login", json={"username": "张三", "password": "123456"}).json()["access_token"]
    H, SH = h(tok), h(stok)

    # 1 学生无权修改
    r = requests.put(f"{BASE}/api/carbon/records/1", json={}, headers=SH)
    print("1 student PUT:", r.status_code)
    assert r.status_code == 403

    # 2 找一条 2026-05 教学楼A 记录
    rows = requests.get(f"{BASE}/api/carbon/records", headers=H).json()
    target = next(r for r in rows if r["building"] == "教学楼A" and r["year"] == 2026 and r["month"] == 5)
    orig = dict(target)
    print("2 target:", target["id"], "elec", target["electricity_kwh"], "semester", target["semester"])

    # 3 修改用电量并改月份，验证重算与学期重推导
    keys = ["building", "year", "month", "electricity_kwh", "night_electricity_kwh",
            "natural_gas_m3", "gasoline_l", "pv_kwh", "storage_kwh", "saving_kwh"]
    payload = {k: target[k] for k in keys}
    payload.update(electricity_kwh=40000, month=6)
    d = requests.put(f"{BASE}/api/carbon/records/{target['id']}", json=payload, headers=H).json()
    print("3 after PUT: month", d["month"], "semester", d["semester"], "scope2", d["emissions"]["scope2"])
    assert d["month"] == 6 and d["semester"] == "2025-2026-2"
    assert abs(d["emissions"]["scope2"] - 40000 * 0.5703) < 0.01

    # 4 GET 确认已落库
    rows2 = requests.get(f"{BASE}/api/carbon/records", headers=H).json()
    got = next(r for r in rows2 if r["id"] == target["id"])
    assert got["electricity_kwh"] == 40000 and got["month"] == 6

    # 5 恢复原值
    payload.update(electricity_kwh=orig["electricity_kwh"], month=orig["month"],
                   night_electricity_kwh=orig["night_electricity_kwh"])
    d2 = requests.put(f"{BASE}/api/carbon/records/{target['id']}", json=payload, headers=H).json()
    print("5 restored: month", d2["month"], "semester", d2["semester"], "elec", d2["electricity_kwh"])
    assert (d2["month"], d2["semester"], d2["electricity_kwh"]) == (orig["month"], orig["semester"], orig["electricity_kwh"])

    # 6 不存在的记录
    r = requests.put(f"{BASE}/api/carbon/records/99999", json=payload, headers=H)
    print("6 missing:", r.status_code)
    assert r.status_code == 404

    print("\nALL PUT CHECKS PASSED")


if __name__ == "__main__":
    main()
