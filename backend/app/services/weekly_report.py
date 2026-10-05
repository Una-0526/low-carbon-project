"""我的碳周报：按周聚合打卡记录与积分流水。

- 自然周以周一为起点；
- 减碳量 = 当周已通过打卡对应任务的碳量之和；打卡次数 = 当周已通过打卡数；
- 积分 = 当周正数流水之和（兑换扣减不计入）；
- 全校排名按当周减碳量，仅当周有打卡的学生参与；
- 已结束的周在启动 / 首次访问时自动生成快照（等效于每周一自动生成上一周周报）。
"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Checkin, PointTransaction, User, WeeklyReport
from app.services.checkin_service import TASK_CARBON_KG


def monday_of(d: date) -> date:
    """所在自然周的周一。"""
    return d - timedelta(days=d.weekday())


def _empty_stats() -> dict:
    return {"carbon": 0.0, "count": 0, "points": 0, "tasks": defaultdict(int)}


def _aggregate(db: Session, start: datetime, end: datetime) -> dict[int, dict]:
    """聚合 [start, end) 一周内全校学生的打卡与积分：{user_id: stats}。"""
    stats: dict[int, dict] = defaultdict(_empty_stats)
    rows = db.execute(
        select(Checkin.user_id, Checkin.task_type)
        .where(Checkin.status == "approved", Checkin.created_at >= start, Checkin.created_at < end)
    ).all()
    for uid, task in rows:
        s = stats[uid]
        s["carbon"] += TASK_CARBON_KG.get(task, 0.0)
        s["count"] += 1
        s["tasks"][task] += 1
    rows = db.execute(
        select(PointTransaction.user_id, PointTransaction.points)
        .where(PointTransaction.points > 0, PointTransaction.created_at >= start, PointTransaction.created_at < end)
    ).all()
    for uid, pts in rows:
        stats[uid]["points"] += pts
    return stats


def _carbon_ranks(week_stats: dict[int, dict]) -> dict[int, int]:
    """当周减碳量名次：有打卡才参与，碳量高者在前，同碳量按 user_id 升序。"""
    active = {uid: s["carbon"] for uid, s in week_stats.items() if s["count"] > 0}
    ordered = sorted(active.items(), key=lambda kv: (-kv[1], kv[0]))
    return {uid: i + 1 for i, (uid, _) in enumerate(ordered)}


def _summary(s: dict, rank: int | None, rank_change: int | None) -> str:
    """生成一句个性化总结建议。"""
    if s["count"] == 0:
        return "本周还没有绿色打卡记录，完成任意一次打卡就能积累减碳量啦"
    top_task, top_n = max(s["tasks"].items(), key=lambda kv: kv[1])
    parts = [f"本周{top_task}{top_n}次减碳{s['carbon']:.1f}kg"]
    if rank:
        parts.append(f"全校第{rank}名")
    if rank_change is not None and rank_change != 0:
        parts.append(f"较上周{'上升' if rank_change > 0 else '下降'}{abs(rank_change)}名")
    elif rank_change == 0:
        parts.append("较上周持平")
    # 建议：优先推荐本周没做过的任务中碳量最高的；都做过则推荐做得最少的
    not_done = [t for t in TASK_CARBON_KG if t not in s["tasks"]]
    sug = max(not_done, key=TASK_CARBON_KG.get) if not_done else min(s["tasks"], key=s["tasks"].get)
    return "，".join(parts) + f"；建议增加{sug}打卡"


def compute_week_card(db: Session, user: User) -> dict:
    """实时计算本周碳周报卡片（本周为进行中的周，不落库）。"""
    this_ws = monday_of(date.today())
    last_ws = this_ws - timedelta(days=7)
    cur_all = _aggregate(db, datetime(this_ws.year, this_ws.month, this_ws.day),
                         datetime(this_ws.year, this_ws.month, this_ws.day) + timedelta(days=7))
    last_all = _aggregate(db, datetime(last_ws.year, last_ws.month, last_ws.day),
                          datetime(last_ws.year, last_ws.month, last_ws.day) + timedelta(days=7))
    cur = cur_all.get(user.id) or _empty_stats()
    last = last_all.get(user.id) or _empty_stats()
    cur_ranks, last_ranks = _carbon_ranks(cur_all), _carbon_ranks(last_all)
    rank, prev_rank = cur_ranks.get(user.id), last_ranks.get(user.id)
    rank_change = (prev_rank - rank) if (rank and prev_rank) else None
    carbon_change = round(cur["carbon"] - last["carbon"], 2)
    return {
        "week_start": this_ws,
        "carbon_kg": round(cur["carbon"], 2),
        "points": cur["points"],
        "checkin_count": cur["count"],
        "carbon_change": carbon_change,
        "rank": rank,
        "rank_change": rank_change,
        "summary": _summary(cur, rank, rank_change),
    }


def ensure_weekly_reports(db: Session) -> None:
    """为所有学生补齐已完成周（截至上周）的周报快照，缺哪周补哪周（幂等）。"""
    today = date.today()
    last_week_start = monday_of(today) - timedelta(days=7)

    # 全部历史按 (user, 周一) 聚合一次，再按周从旧到新扫描生成
    stats: dict[tuple[int, date], dict] = defaultdict(_empty_stats)
    rows = db.execute(
        select(Checkin.user_id, Checkin.task_type, Checkin.created_at).where(Checkin.status == "approved")
    ).all()
    for uid, task, created in rows:
        s = stats[(uid, monday_of(created.date()))]
        s["carbon"] += TASK_CARBON_KG.get(task, 0.0)
        s["count"] += 1
        s["tasks"][task] += 1
    rows = db.execute(
        select(PointTransaction.user_id, PointTransaction.points, PointTransaction.created_at)
        .where(PointTransaction.points > 0)
    ).all()
    for uid, pts, created in rows:
        stats[(uid, monday_of(created.date()))]["points"] += pts

    existing = {(r.user_id, r.week_start) for r in db.scalars(select(WeeklyReport)).all()}
    by_week: dict[date, list[tuple[int, dict]]] = defaultdict(list)
    for (uid, ws), s in stats.items():
        by_week[ws].append((uid, s))

    last_rank_info: dict[int, tuple[date, int]] = {}  # uid -> (周一份, 当周名次)
    new_rows: list[WeeklyReport] = []
    for ws in sorted(by_week):
        if ws > last_week_start:
            break  # 本周进行中，不生成快照
        rank_map = _carbon_ranks({uid: s for uid, s in by_week[ws]})
        for uid, s in by_week[ws]:
            rank = rank_map.get(uid)
            prev = last_rank_info.get(uid)
            # 名次变化严格对比上一周（跳过周不跨周比较）
            rank_change = (prev[1] - rank) if (rank and prev and prev[0] == ws - timedelta(days=7)) else None
            if rank:
                last_rank_info[uid] = (ws, rank)
            if (uid, ws) in existing or (s["count"] == 0 and s["points"] == 0):
                continue  # 已生成过，或该周无任何活动：不生成空周报
            new_rows.append(WeeklyReport(
                user_id=uid,
                week_start=ws,
                carbon_kg=round(s["carbon"], 2),
                points=s["points"],
                checkin_count=s["count"],
                rank=rank,
                rank_change=rank_change,
                summary=_summary(s, rank, rank_change),
            ))
    if new_rows:
        db.add_all(new_rows)
        db.commit()


def list_history(db: Session, user: User) -> list[WeeklyReport]:
    """当前学生的历史周报（新→旧），访问时先补齐缺失周。"""
    ensure_weekly_reports(db)
    return list(
        db.scalars(
            select(WeeklyReport)
            .where(WeeklyReport.user_id == user.id)
            .order_by(WeeklyReport.week_start.desc())
        ).all()
    )
