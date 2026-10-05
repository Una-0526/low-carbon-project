"""碳积分排行榜：个人 / 宿舍 / 班级 × 本月 / 本年。

积分口径：按流水发生时间统计当期"获得"的积分（正数流水），
兑换扣减等负数流水不计入排名。
较上期名次变化 = 上个自然月 / 上个自然年名次 - 当期名次（正数表示上升）。
"""
import calendar
import random
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import Checkin, PointTransaction, User
from app.services import point_service
from app.services.checkin_service import TASK_POINTS

DEMO_PASSWORD = "123456"
# 种子幂等标记：以第一个模拟学生是否存在为准
_SIM_MARK = "王晓华"

# 模拟学生（姓名, 班级, 宿舍）：4 个班级 / 4 个宿舍交叉分布
SIM_STUDENTS: list[tuple[str, str, str]] = [
    ("王晓华", "计算机2401班", "桃园3栋302"),
    ("李子航", "计算机2401班", "桃园3栋401"),
    ("陈雨桐", "计算机2401班", "梅园1栋205"),
    ("刘俊杰", "计算机2402班", "桃园3栋302"),
    ("赵欣然", "计算机2402班", "桃园3栋401"),
    ("孙浩然", "计算机2402班", "梅园1栋205"),
    ("周美玲", "计算机2402班", "梅园1栋502"),
    ("吴思远", "土木2401班", "桃园3栋302"),
    ("郑晓峰", "土木2401班", "梅园1栋205"),
    ("冯雅婷", "土木2401班", "桃园3栋401"),
    ("蒋文博", "土木2402班", "梅园1栋502"),
    ("韩雪莹", "土木2402班", "梅园1栋205"),
]

# 与 checkin_service.TASK_POINTS 同口径的打卡档位（避免循环依赖，此处静态列出）
_SIM_TASKS: list[tuple[str, int]] = [
    ("骑行", 10), ("随手关灯", 2), ("光盘", 5), ("自带水杯", 3), ("爬楼", 3),
]
# 寒暑假月份打卡频率明显降低
_VACATION_MONTHS = {1, 2, 7, 8}


def _back_month(now: datetime, back: int) -> tuple[int, int]:
    """back=0 返回当前 (年, 月)，back=1 上个月，以此类推。"""
    total = now.year * 12 + (now.month - 1) - back
    return total // 12, total % 12 + 1


def ensure_demo_leaderboard_data(db: Session) -> None:
    """首次启动时补充模拟学生与近 12 个月积分流水（幂等，张三的真实数据不动）。"""
    if db.scalar(select(User.id).where(User.username == _SIM_MARK)) is not None:
        return
    users = [
        User(username=name, password_hash=hash_password(DEMO_PASSWORD),
             role="student", class_name=cls, dormitory=dorm)
        for name, cls, dorm in SIM_STUDENTS
    ]
    db.add_all(users)
    db.flush()  # 拿到 user.id

    rng = random.Random(42)  # 固定种子，每次生成的数据一致
    now = datetime.now()
    for u in users:
        for back in range(12):  # 近 12 个月（含当月，当月截至今天）
            y, m = _back_month(now, back)
            max_day = now.day if back == 0 else calendar.monthrange(y, m)[1]
            if max_day < 1:
                continue
            n_tx = rng.randint(1, 3) if m in _VACATION_MONTHS else rng.randint(3, 6)
            for _ in range(n_tx):
                task, pts = rng.choice(_SIM_TASKS)
                day = rng.randint(1, max_day)
                created = datetime(y, m, day, rng.randint(8, 21), rng.randint(0, 59))
                point_service.credit(db, u.id, pts, "checkin", None,
                                     f"打卡通过：{task}", created_at=created)
                if rng.random() < 0.12:  # 偶尔发一笔连续打卡奖励
                    bonus = rng.choice([5, 10, 20])
                    point_service.credit(db, u.id, bonus, "streak_bonus", None,
                                         "连续打卡奖励", created_at=created)
    db.commit()


def ensure_demo_checkins(db: Session) -> None:
    """为模拟学生按已生成的积分流水补建"已通过"打卡记录（幂等）。

    周报 / 碳诊断等按打卡记录聚合的功能依赖 checkins 表，
    模拟学生只有流水没有打卡，这里从 reason=checkin 的流水反推补齐。
    """
    sim_ids = list(db.scalars(
        select(User.id).where(User.username.in_([name for name, _, _ in SIM_STUDENTS]))
    ).all())
    if not sim_ids:
        return
    if db.scalar(select(Checkin.id).where(Checkin.user_id.in_(sim_ids)).limit(1)) is not None:
        return
    txs = db.scalars(
        select(PointTransaction).where(
            PointTransaction.user_id.in_(sim_ids), PointTransaction.reason == "checkin"
        )
    ).all()
    for tx in txs:
        task = (tx.description or "").split("：", 1)[-1]
        if task not in TASK_POINTS:
            continue
        db.add(Checkin(
            user_id=tx.user_id,
            task_type=task,
            status="approved",
            points_awarded=TASK_POINTS[task],
            created_at=tx.created_at,
        ))
    db.commit()


def _earned_map(db: Session, start: datetime, end: datetime | None = None) -> dict[int, int]:
    """当期获得积分（正数流水）按用户汇总：{user_id: points}。"""
    query = select(PointTransaction.user_id, func.sum(PointTransaction.points)).where(
        PointTransaction.points > 0,
        PointTransaction.created_at >= start,
    )
    if end is not None:
        query = query.where(PointTransaction.created_at < end)
    rows = db.execute(query.group_by(PointTransaction.user_id)).all()
    return {uid: int(total) for uid, total in rows}


def _ranks(score_map: dict[int, int]) -> dict[int, int]:
    """名次：分高在前，同分按 user_id 升序。"""
    ordered = sorted(score_map.items(), key=lambda kv: (-kv[1], kv[0]))
    return {uid: i + 1 for i, (uid, _) in enumerate(ordered)}


def _period_starts(now: datetime, period: str) -> tuple[datetime, datetime]:
    """返回 (当期起始, 上期起始)。month → 本月 1 日 / 上月 1 日；year → 今年 / 去年 1 月 1 日。"""
    if period == "year":
        return datetime(now.year, 1, 1), datetime(now.year - 1, 1, 1)
    py, pm = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
    return datetime(now.year, now.month, 1), datetime(py, pm, 1)


def _personal_items(db: Session, cur_start: datetime, prev_start: datetime) -> list[dict]:
    cur = _earned_map(db, cur_start)
    prev_ranks = _ranks(_earned_map(db, prev_start, cur_start))
    cur_ranks = _ranks(cur)
    students = {
        u.id: u for u in db.scalars(select(User).where(User.role == "student")).all()
    }
    items = []
    for uid, pts in sorted(cur.items(), key=lambda kv: (-kv[1], kv[0])):
        u = students.get(uid)
        if u is None:
            continue
        prev_rank = prev_ranks.get(uid)
        items.append({
            "rank": cur_ranks[uid],
            "key": u.username,
            "user_id": uid,
            "username": u.username,
            "class_name": u.class_name,
            "dormitory": u.dormitory,
            "points": pts,
            "rank_change": (prev_rank - cur_ranks[uid]) if prev_rank else None,
        })
    return items


def _group_items(db: Session, field: str, cur_start: datetime) -> list[dict]:
    """按宿舍（dormitory）或班级（class_name）聚合：积分为当期成员获得之和，人数为该组全部学生。"""
    earned = _earned_map(db, cur_start)
    members: dict[str, list[User]] = {}
    for u in db.scalars(select(User).where(User.role == "student")).all():
        key = getattr(u, field)
        if key:
            members.setdefault(key, []).append(u)
    rows = [
        {"key": key, "member_count": len(us), "points": sum(earned.get(u.id, 0) for u in us)}
        for key, us in members.items()
    ]
    rows.sort(key=lambda r: (-r["points"], r["key"]))
    return [{"rank": i + 1, "points": r["points"], "member_count": r["member_count"], "key": r["key"]}
            for i, r in enumerate(rows)]


def build(db: Session, user: User, board_type: str, period: str) -> dict:
    """组装排行榜响应：items 全量 + me（当前学生定位，教师为 None）。"""
    cur_start, prev_start = _period_starts(datetime.now(), period)
    if board_type == "personal":
        items = _personal_items(db, cur_start, prev_start)
        me_match = lambda it: it["key"] == user.username  # noqa: E731
    elif board_type == "dorm":
        items = _group_items(db, "dormitory", cur_start)
        me_match = lambda it: it["key"] == user.dormitory  # noqa: E731
    else:
        items = _group_items(db, "class_name", cur_start)
        me_match = lambda it: it["key"] == user.class_name  # noqa: E731
    me = next((it for it in items if user.role == "student" and me_match(it)), None)
    return {"type": board_type, "period": period, "items": items, "me": me}
