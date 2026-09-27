"""绿色打卡服务：防作弊检查、连续打卡统计、审核与积分入账。"""

import json
from datetime import date, datetime, timedelta
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Checkin, User
from app.services import point_service

# 打卡任务类型与基础积分
TASK_POINTS: dict[str, int] = {
    "骑行": 10,
    "随手关灯": 2,
    "光盘": 5,
    "自带水杯": 3,
    "爬楼": 3,
}

# 各任务单次减碳量（kgCO2e）：骑行 5 次/周约 2kg
TASK_CARBON_KG: dict[str, float] = {
    "骑行": 0.4,
    "光盘": 0.2,
    "自带水杯": 0.1,
    "爬楼": 0.05,
    "随手关灯": 0.05,
}

# 行为分类：出行 / 饮食 / 节约用电
TASK_CATEGORY: dict[str, str] = {
    "骑行": "出行",
    "光盘": "饮食",
    "自带水杯": "饮食",
    "随手关灯": "节约用电",
    "爬楼": "节约用电",
}
CATEGORIES: list[str] = ["出行", "饮食", "节约用电"]

# 连续打卡里程碑奖励：连续天数 -> 额外积分
STREAK_BONUS: dict[int, int] = {3: 5, 7: 10, 14: 20, 30: 50}

MIN_INTERVAL_MINUTES = 5  # 同类型打卡最小间隔
MAX_DORM_DISTANCE_KM = 2.0  # 距宿舍最大距离（超出判为位置漂移）


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """球面两点距离（km）。"""
    r = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    h = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(h))


def run_anti_cheat(db: Session, user, task_type: str, latitude: float | None, longitude: float | None) -> list[str]:
    """AI 防作弊检查，返回命中的规则列表。"""
    flags: list[str] = []

    # 规则 1：同类型打卡间隔 < 5 分钟
    recent = db.scalar(
        select(Checkin)
        .where(
            Checkin.user_id == user.id,
            Checkin.task_type == task_type,
            Checkin.created_at > datetime.now() - timedelta(minutes=MIN_INTERVAL_MINUTES),
        )
        .order_by(Checkin.created_at.desc())
    )
    if recent:
        flags.append(f"同类型打卡间隔不足 {MIN_INTERVAL_MINUTES} 分钟")

    # 规则 2：位置漂移——定位距宿舍超过 2km
    if (
        latitude is not None
        and longitude is not None
        and user.dorm_latitude is not None
        and user.dorm_longitude is not None
    ):
        dist = haversine_km(latitude, longitude, user.dorm_latitude, user.dorm_longitude)
        if dist > MAX_DORM_DISTANCE_KM:
            flags.append(f"打卡位置距宿舍 {dist:.2f}km，超过 {MAX_DORM_DISTANCE_KM}km 阈值（疑似位置漂移）")

    return flags


def create_checkin(
    db: Session,
    user,
    task_type: str,
    latitude: float | None,
    longitude: float | None,
    photo_path: str | None,
    note: str | None = None,
) -> tuple[Checkin, list[str]]:
    """创建打卡记录（待审核），同时执行防作弊检查。"""
    flags = run_anti_cheat(db, user, task_type, latitude, longitude)
    checkin = Checkin(
        user_id=user.id,
        task_type=task_type,
        photo_path=photo_path,
        latitude=latitude,
        longitude=longitude,
        note=note,
        ai_flagged=bool(flags),
        ai_flags=json.dumps(flags, ensure_ascii=False),
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin, flags


def calc_streak(db: Session, user_id: int, on_date: date) -> int:
    """截至 on_date（含）的连续已通过打卡天数。"""
    dates = {
        row[0]
        for row in db.execute(
            select(func.date(Checkin.created_at)).where(
                Checkin.user_id == user_id, Checkin.status == "approved"
            )
        ).all()
    }
    streak, d = 0, on_date
    while d.isoformat() in dates:
        streak += 1
        d -= timedelta(days=1)
    return streak


def approve_checkin(db: Session, checkin: Checkin) -> dict:
    """审核通过：积分入账 + 命中里程碑时发放连续奖励。返回 {streak, bonus}。"""
    if checkin.status != "pending":
        raise ValueError("该打卡已审核，不能重复操作")

    checkin.status = "approved"
    base = TASK_POINTS.get(checkin.task_type, 0)
    checkin.points_awarded = base
    point_service.credit(db, checkin.user_id, base, "checkin", checkin.id, f"打卡通过：{checkin.task_type}")
    # 会话配置了 autoflush=False，先落库让下面的查询能看到本条记录
    db.flush()

    streak = calc_streak(db, checkin.user_id, checkin.created_at.date())
    # 里程碑奖励按天发放：同一天已审核过其它打卡时不再重复发
    date_str = checkin.created_at.date().isoformat()
    first_of_day = (
        db.scalar(
            select(Checkin.id).where(
                Checkin.user_id == checkin.user_id,
                Checkin.status == "approved",
                func.date(Checkin.created_at) == date_str,
                Checkin.id != checkin.id,
            ).limit(1)
        )
        is None
    )
    bonus = STREAK_BONUS.get(streak, 0) if first_of_day else 0
    if bonus:
        point_service.credit(
            db, checkin.user_id, bonus, "streak_bonus", checkin.id, f"连续打卡 {streak} 天奖励"
        )
    db.commit()
    db.refresh(checkin)
    return {"streak": streak, "bonus": bonus}


def reject_checkin(db: Session, checkin: Checkin, reason: str | None) -> Checkin:
    """审核驳回：不发积分，记录原因。"""
    if checkin.status != "pending":
        raise ValueError("该打卡已审核，不能重复操作")
    checkin.status = "rejected"
    checkin.review_reason = reason
    db.commit()
    db.refresh(checkin)
    return checkin


def student_summary(db: Session, user_id: int) -> dict:
    """学生端汇总：累计积分 + 当前连续天数（最近一次打卡在今天或昨天才算连续）。"""
    total = point_service.total(db, user_id)
    last = db.scalar(
        select(func.date(Checkin.created_at))
        .where(Checkin.user_id == user_id, Checkin.status == "approved")
        .order_by(func.date(Checkin.created_at).desc())
        .limit(1)
    )
    streak = 0
    if last:
        last_date = date.fromisoformat(str(last))
        if (date.today() - last_date).days <= 1:
            streak = calc_streak(db, user_id, last_date)
    return {"total_points": total, "streak_days": streak}


def _week_start(today: date) -> datetime:
    """本周一 00:00。"""
    return datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())


def _month_start(today: date) -> datetime:
    """本月 1 日 00:00。"""
    return datetime.combine(today.replace(day=1), datetime.min.time())


def _build_advice(weekly: dict[str, int], categories_active: set[str]) -> list[str]:
    """按本周各任务打卡次数生成个性化建议。"""
    advice: list[str] = []
    rides = weekly.get("骑行", 0)
    if rides == 0:
        advice.append("本周骑行为 0 次，建议骑行上学，每周可减碳约 2kg")
    elif rides < 3:
        advice.append(f"本周骑行 {rides} 次，再多骑几次通勤，每周还能多减碳约 1kg")
    else:
        advice.append(f"本周骑行 {rides} 次，绿色出行表现出色，继续保持")
    if weekly.get("随手关灯", 0) == 0:
        advice.append("本周还没有随手关灯打卡，离开教室和宿舍记得关灯省电")
    if weekly.get("光盘", 0) == 0:
        advice.append("本周还没有光盘打卡，按需取餐不浪费，每次约减碳 0.2kg")
    if weekly.get("自带水杯", 0) == 0:
        advice.append("建议自带水杯，减少一次性纸杯与瓶装水的使用")
    if weekly.get("爬楼", 0) == 0:
        advice.append("3 层以内建议爬楼梯代替电梯，低碳又能锻炼身体")
    if len(categories_active) == len(CATEGORIES):
        advice.append("本周出行、饮食、节约用电三类行为全覆盖，非常全面，继续保持！")
    return advice


def my_diagnosis(db: Session, user) -> dict:
    """学生碳诊断：本周/本月减碳、分类统计、个性化建议、月度班级排名百分位。"""
    today = date.today()
    rows = db.execute(
        select(Checkin.task_type, Checkin.created_at)
        .where(Checkin.user_id == user.id, Checkin.status == "approved")
    ).all()
    week_start, month_start = _week_start(today), _month_start(today)

    weekly: dict[str, int] = {}
    week_carbon = week_count = month_carbon = month_count = 0.0
    month_carbon_by_user: dict[int, float] = {}
    for task_type, created_at in rows:
        kg = TASK_CARBON_KG.get(task_type, 0.0)
        if created_at >= week_start:
            weekly[task_type] = weekly.get(task_type, 0) + 1
            week_carbon += kg
            week_count += 1
        if created_at >= month_start:
            month_carbon += kg
            month_count += 1
            month_carbon_by_user[user.id] = month_carbon_by_user.get(user.id, 0.0) + kg

    categories = []
    for cat in CATEGORIES:
        tasks = [t for t, c in TASK_CATEGORY.items() if c == cat]
        count = sum(weekly.get(t, 0) for t in tasks)
        categories.append({
            "category": cat,
            "week_count": count,
            "week_carbon_kg": round(sum(weekly.get(t, 0) * TASK_CARBON_KG.get(t, 0.0) for t in tasks), 2),
        })

    # 月度报告：班级内按本月减碳排名，百分位 = 超过班级同学的百分比
    report = {
        "month": f"{today.year}-{today.month:02d}",
        "carbon_kg": round(month_carbon, 2),
        "checkin_count": month_count,
        "class_name": user.class_name,
        "rank": None, "class_size": None, "percentile": None,
    }
    if user.class_name:
        classmates = db.scalars(
            select(User).where(User.role == "student", User.class_name == user.class_name)
        ).all()
        ids = [u.id for u in classmates if u.id != user.id]
        others: dict[int, float] = {}
        if ids:
            for uid, task_type in db.execute(
                select(Checkin.user_id, Checkin.task_type)
                .where(Checkin.user_id.in_(ids), Checkin.status == "approved",
                       Checkin.created_at >= month_start)
            ).all():
                others[uid] = others.get(uid, 0.0) + TASK_CARBON_KG.get(task_type, 0.0)
        my = month_carbon_by_user.get(user.id, 0.0)
        better = sum(1 for v in others.values() if v > my)
        worse = sum(1 for v in others.values() if v < my)
        size = len(ids) + 1
        report.update(
            rank=better + 1,
            class_size=size,
            percentile=round(worse / (size - 1) * 100) if size > 1 else 100,
        )

    return {
        "week_carbon_kg": round(week_carbon, 2),
        "week_count": week_count,
        "month_carbon_kg": round(month_carbon, 2),
        "month_count": month_count,
        "total_points": point_service.total(db, user.id),
        "streak_days": student_summary(db, user.id)["streak_days"],
        "categories": categories,
        "advice": _build_advice(weekly, {c["category"] for c in categories if c["week_count"] > 0}),
        "monthly_report": report,
    }
