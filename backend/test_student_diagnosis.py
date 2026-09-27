"""学生碳诊断接口测试。

前置：backend 服务已启动。运行：python test_student_diagnosis.py
"""
import os
from datetime import datetime, timedelta

import requests

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")

TASK_CARBON_KG = {"骑行": 0.4, "光盘": 0.2, "自带水杯": 0.1, "爬楼": 0.05, "随手关灯": 0.05}


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    stok = requests.post(f"{BASE}/api/auth/login", json={"username": "张三", "password": "123456"}).json()["access_token"]
    tok = requests.post(f"{BASE}/api/auth/login", json={"username": "李老师", "password": "123456"}).json()["access_token"]

    # 1 鉴权：无 token 401；教师可访问自己的诊断（与 /me、/points/me 端点一致），数据为空态
    print("1 no token:", requests.get(f"{BASE}/api/checkins/me/diagnosis").status_code)
    assert requests.get(f"{BASE}/api/checkins/me/diagnosis").status_code == 401
    td = requests.get(f"{BASE}/api/checkins/me/diagnosis", headers=h(tok)).json()
    print("1 teacher self-diagnosis: week", td["week_carbon_kg"], "| rank", td["monthly_report"]["rank"])
    assert td["week_carbon_kg"] == 0.0 and td["monthly_report"]["rank"] is None

    # 2 结构
    d = requests.get(f"{BASE}/api/checkins/me/diagnosis", headers=h(stok)).json()
    print("2 keys:", sorted(d.keys()))
    assert all(k in d for k in ["week_carbon_kg", "week_count", "month_carbon_kg", "month_count",
                                "total_points", "streak_days", "categories", "advice", "monthly_report"])
    assert [c["category"] for c in d["categories"]] == ["出行", "饮食", "节约用电"]
    assert len(d["advice"]) >= 1
    print("2 advice:", d["advice"])

    # 3 数学口径：与 /checkins/me 中已通过记录逐条对照
    checkins = requests.get(f"{BASE}/api/checkins/me", headers=h(stok)).json()
    now = datetime.now()
    week_start = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    exp_week = sum(TASK_CARBON_KG.get(c["task_type"], 0) for c in checkins
                   if c["status"] == "approved" and datetime.fromisoformat(c["created_at"]) >= week_start)
    exp_month = sum(TASK_CARBON_KG.get(c["task_type"], 0) for c in checkins
                    if c["status"] == "approved" and datetime.fromisoformat(c["created_at"]) >= month_start)
    print(f"3 week: api {d['week_carbon_kg']} vs expect {round(exp_week, 2)} | month: api {d['month_carbon_kg']} vs expect {round(exp_month, 2)}")
    assert d["week_carbon_kg"] == round(exp_week, 2) and d["month_carbon_kg"] == round(exp_month, 2)

    # 4 月度报告与排名
    r = d["monthly_report"]
    print("4 report:", r)
    assert r["month"] == f"{now.year}-{now.month:02d}"
    if r["class_name"]:
        assert 1 <= r["rank"] <= r["class_size"]
        assert 0 <= r["percentile"] <= 100
    else:
        assert r["rank"] is None

    print("\nALL DIAGNOSIS CHECKS PASSED")


if __name__ == "__main__":
    main()
