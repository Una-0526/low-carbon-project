"""打卡功能全流程测试：防作弊、照片上传、审核、积分与连续奖励。

可重复运行：开头清空打卡/积分测试数据并回填前两天已通过的打卡。
"""

from datetime import datetime, timedelta

import requests

from app.database import SessionLocal
from app.models import Checkin, PointTransaction, User

BASE = "http://127.0.0.1:8000"

# ---- 重置测试数据：清空 checkins / point_transactions，回填两条历史已通过打卡 ----
_db = SessionLocal()
_db.query(PointTransaction).delete()
_db.query(Checkin).delete()
_zs = _db.query(User).filter_by(username="张三").first()
_now = datetime.now()
_db.add_all([
    Checkin(user_id=_zs.id, task_type="骑行", status="approved", points_awarded=10,
            created_at=_now - timedelta(days=2)),
    Checkin(user_id=_zs.id, task_type="爬楼", status="approved", points_awarded=3,
            created_at=_now - timedelta(days=1)),
])
_db.commit()
_db.close()
print("== test data reset ==")


def login(username, password):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def h(token):
    return {"Authorization": f"Bearer {token}"}


stok = login("张三", "123456")
ttok = login("李老师", "123456")

# 1 正常打卡（宿舍附近，无照片）
r = requests.post(f"{BASE}/api/checkins", headers=h(stok),
                  data={"task_type": "光盘", "latitude": "30.6605", "longitude": "104.0658"})
d = r.json()
print("1 normal:", r.status_code, d["status"], "flagged=", d["ai_flagged"], d["ai_flags"])
assert r.status_code == 201 and d["ai_flagged"] is False and d["status"] == "pending"
normal_id = d["id"]

# 2 同类型间隔 < 5 分钟 → 标记
r = requests.post(f"{BASE}/api/checkins", headers=h(stok), data={"task_type": "光盘"})
d = r.json()
print("2 interval flagged:", d["ai_flagged"], d["ai_flags"])
assert d["ai_flagged"] is True and any("间隔" in f for f in d["ai_flags"])
dup_id = d["id"]

# 3 位置漂移（距宿舍 > 2km）→ 标记
r = requests.post(f"{BASE}/api/checkins", headers=h(stok),
                  data={"task_type": "骑行", "latitude": "30.6800", "longitude": "104.0650"})
d = r.json()
print("3 drift flagged:", d["ai_flagged"], d["ai_flags"])
assert d["ai_flagged"] is True and any("km" in f for f in d["ai_flags"])

# 4 照片上传打卡
with open("_test_photo.png", "rb") as f:
    r = requests.post(f"{BASE}/api/checkins", headers=h(stok),
                      data={"task_type": "自带水杯", "latitude": "30.6602", "longitude": "104.0652"},
                      files={"photo": ("cup.png", f, "image/png")})
d = r.json()
print("4 photo:", r.status_code, d["photo_path"])
assert r.status_code == 201 and d["photo_path"]

# 5 照片可访问
r = requests.get(BASE + d["photo_path"])
print("5 photo serve:", r.status_code, len(r.content), "bytes")
assert r.status_code == 200

# 6 学生汇总（审核前：前两天 2 条已通过 → 连续 2 天，积分 0）
r = requests.get(f"{BASE}/api/checkins/me/summary", headers=h(stok))
d = r.json()
print("6 summary before:", d)
assert d == {"total_points": 0, "streak_days": 2}

# 7 教师查待审列表
r = requests.get(f"{BASE}/api/checkins", headers=h(ttok), params={"status": "pending"})
d = r.json()
print("7 pending:", len(d))
assert len(d) == 4

# 8 审核通过 → 基础 5 分 + 连续 3 天奖励 5 分
r = requests.post(f"{BASE}/api/checkins/{normal_id}/approve", headers=h(ttok))
d = r.json()
print("8 approve:", d["checkin"]["points_awarded"], "pts, streak", d["streak"], ", bonus", d["bonus"])
assert d["checkin"]["points_awarded"] == 5 and d["streak"] == 3 and d["bonus"] == 5

# 9 驳回重复打卡
r = requests.post(f"{BASE}/api/checkins/{dup_id}/reject", headers=h(ttok), json={"reason": "间隔不足 5 分钟"})
d = r.json()
print("9 reject:", d["status"], d["review_reason"])
assert d["status"] == "rejected" and d["review_reason"]

# 10 学生汇总（审核后：积分 10，连续 3 天）
r = requests.get(f"{BASE}/api/checkins/me/summary", headers=h(stok))
d = r.json()
print("10 summary after:", d)
assert d == {"total_points": 10, "streak_days": 3}

# 11 学生积分流水
r = requests.get(f"{BASE}/api/points/me", headers=h(stok))
d = r.json()
print("11 points/me:", d["total_points"], [(t["reason"], t["points"]) for t in d["transactions"]])
assert d["total_points"] == 10 and {t["reason"] for t in d["transactions"]} == {"checkin", "streak_bonus"}

# 12 学生访问教师接口 → 403
r = requests.get(f"{BASE}/api/checkins", headers=h(stok))
print("12 student->teacher list:", r.status_code)
assert r.status_code == 403

# 13 无 token → 401
r = requests.post(f"{BASE}/api/checkins", data={"task_type": "光盘"})
print("13 no token:", r.status_code)
assert r.status_code == 401

# 14 无效任务类型 → 400
r = requests.post(f"{BASE}/api/checkins", headers=h(stok), data={"task_type": "旷课"})
print("14 invalid task:", r.status_code)
assert r.status_code == 400

# 15 教师查学生流水
uid = requests.get(f"{BASE}/api/checkins", headers=h(ttok), params={"ai_flagged": False}).json()[0]["user_id"]
r = requests.get(f"{BASE}/api/points/transactions", headers=h(ttok), params={"user_id": uid})
d = r.json()
print("15 teacher view points:", d["total_points"], len(d["transactions"]))
assert d["total_points"] == 10

print("\nALL 15 CHECKS PASSED")
