"""异常诊断 / 方案库接口测试（可重复运行，不影响 energy_records 数据）。

前置：backend 服务已启动（uvicorn app.main:app --port 8000）。
运行：python test_diagnosis_api.py
"""
import requests

BASE = "http://127.0.0.1:8000"


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(username: str) -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": "123456"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def main() -> None:
    ttok = login("李老师")
    stok = login("张三")

    # 1 未登录 / 越权
    r = requests.get(f"{BASE}/api/diagnosis/buildings")
    print("1 no token:", r.status_code)
    assert r.status_code == 401
    r = requests.get(f"{BASE}/api/diagnosis/buildings", headers=h(stok))
    print("1 student:", r.status_code)
    assert r.status_code == 403

    # 2 建筑诊断：图书馆应为异常（空调未关）
    rows = requests.get(f"{BASE}/api/diagnosis/buildings", headers=h(ttok)).json()
    lib = next(r for r in rows if r["building"] == "图书馆")
    print("2 图书馆:", lib["status"], f"环比+{lib['mom_change_pct']}% 夜间{lib['night_ratio_pct']}%")
    print("  结论:", lib["message"])
    assert lib["status"] == "异常"
    assert lib["mom_change_pct"] > 15 and lib["night_ratio_pct"] > 40
    assert "空调未关" in lib["message"]
    ta = next(r for r in rows if r["building"] == "教学楼A")
    print("2 教学楼A:", ta["status"], ta["message"])
    assert ta["status"] == "正常"

    # 3 方案库默认 4 条（清理上次运行残留的测试方案）+ 测算数值校验
    for s in requests.get(f"{BASE}/api/diagnosis/solutions", headers=h(ttok)).json():
        if s["name"] == "测试风能路灯":
            requests.delete(f"{BASE}/api/diagnosis/solutions/{s['id']}", headers=h(ttok))
    sols = requests.get(f"{BASE}/api/diagnosis/solutions", headers=h(ttok)).json()
    print("3 solutions:", len(sols), [s["name"] for s in sols])
    assert len(sols) == 4
    pv = next(s for s in sols if s["name"] == "屋顶光伏发电")
    print("  光伏:", pv["annual_carbon_reduction_kg"], "kg |", pv["annual_saving_yuan"], "元 | 回收", pv["payback_years"], "年")
    assert pv["annual_carbon_reduction_kg"] == round(600000 * 0.5703, 2)  # 342180.0
    assert pv["annual_saving_yuan"] == 360000.0
    assert pv["payback_years"] == round(1500000 / 360000, 2)  # 4.17

    # 4 新增方案（含自定义因子）→ 测算正确
    r = requests.post(f"{BASE}/api/diagnosis/solutions", headers=h(ttok), json={
        "name": "测试风能路灯", "category": "节能改造", "annual_electricity_kwh": 10000,
        "investment": 50000, "electricity_price": 0.6, "factor": 0.3,
    })
    d = r.json()
    print("4 create:", r.status_code, d["annual_carbon_reduction_kg"], d["payback_years"])
    assert r.status_code == 201
    assert d["annual_carbon_reduction_kg"] == 3000.0  # 10000 × 0.3（自定义因子）
    assert d["annual_saving_yuan"] == 6000.0
    assert d["payback_years"] == round(50000 / 6000, 2)
    sid = d["id"]

    r = requests.post(f"{BASE}/api/diagnosis/solutions", headers=h(ttok), json={
        "name": "测试风能路灯", "category": "节能改造", "annual_electricity_kwh": 1,
        "investment": 1, "electricity_price": 1,
    })
    print("4 duplicate:", r.status_code)
    assert r.status_code == 400

    # 5 修改方案电价 → 回收期重算
    r = requests.put(f"{BASE}/api/diagnosis/solutions/{sid}", headers=h(ttok), json={
        "name": "测试风能路灯", "category": "节能改造", "annual_electricity_kwh": 10000,
        "investment": 50000, "electricity_price": 0.8, "factor": 0.3,
    })
    d = r.json()
    print("5 update:", d["annual_saving_yuan"], d["payback_years"])
    assert d["annual_saving_yuan"] == 8000.0
    assert d["payback_years"] == round(50000 / 8000, 2)

    # 6 删除方案
    r = requests.delete(f"{BASE}/api/diagnosis/solutions/{sid}", headers=h(ttok))
    print("6 delete:", r.status_code)
    assert r.status_code == 200
    sols = requests.get(f"{BASE}/api/diagnosis/solutions", headers=h(ttok)).json()
    assert len(sols) == 4

    print("\nALL DIAGNOSIS CHECKS PASSED")


if __name__ == "__main__":
    main()
