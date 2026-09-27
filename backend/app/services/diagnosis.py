"""建筑异常诊断与节能方案库。

诊断规则（两条同时满足才判定异常）：
- 本月碳排放环比上月 > 15%
- 夜间（22:00-6:00）用电占比 > 40%

诊断结论示例："图书馆 本月超标18.3%，主要原因为下班后空调未关"

方案库测算口径：
- 年减碳量(kgCO2e) = 年覆盖电量(kWh) × 减碳因子（未指定时取电网因子）
- 年省电费(元)     = 年覆盖电量(kWh) × 折算电价(元/kWh)
- 回收期(年)       = 投资(元) ÷ 年省电费(元)
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EnergyRecord, Solution
from app.services import carbon as carbon_service

# 阈值
MOM_THRESHOLD_PCT = 15.0      # 环比增幅阈值 %
NIGHT_RATIO_THRESHOLD_PCT = 40.0  # 夜间用电占比阈值 %

# 默认方案（solutions 表为空时写入，参数可随时修改）
DEFAULT_SOLUTIONS: list[dict] = [
    {"name": "屋顶光伏发电", "category": "光伏", "annual_electricity_kwh": 600000,
     "investment": 1500000, "electricity_price": 0.6,
     "description": "教学楼/宿舍屋顶铺设 500kW 光伏，自发自用抵扣市电"},
    {"name": "储能削峰填谷", "category": "储能", "annual_electricity_kwh": 200000,
     "investment": 800000, "electricity_price": 0.35,
     "description": "500kWh 储能柜，谷时充电峰时放电，按峰谷差价折算每度省 0.35 元"},
    {"name": "LED 照明 + 空调变频改造", "category": "节能改造", "annual_electricity_kwh": 300000,
     "investment": 600000, "electricity_price": 0.6,
     "description": "全校灯具更换 LED、老旧空调加装变频，综合节电约 10%"},
    {"name": "峰谷用电调度策略", "category": "峰谷策略", "annual_electricity_kwh": 150000,
     "investment": 50000, "electricity_price": 0.35,
     "description": "洗衣房/热水等可转移负荷调整到谷时段运行，零投资快速见效"},
]


def prev_month(year: int, month: int) -> tuple[int, int]:
    """上个月的 (year, month)。"""
    return (year - 1, 12) if month == 1 else (year, month - 1)


def ensure_default_solutions(db: Session) -> None:
    """solutions 表为空时写入默认方案。"""
    if db.scalar(select(Solution.id).limit(1)) is not None:
        return
    db.add_all([Solution(**item) for item in DEFAULT_SOLUTIONS])
    db.commit()


def compute_solution(solution: Solution, grid_factor: float) -> dict:
    """方案测算：年减碳量 / 年省电费 / 回收期。"""
    factor = solution.factor if solution.factor is not None else grid_factor
    annual_carbon = solution.annual_electricity_kwh * factor
    annual_saving = solution.annual_electricity_kwh * solution.electricity_price
    payback = solution.investment / annual_saving if annual_saving > 0 else None
    return {
        "annual_carbon_reduction_kg": round(annual_carbon, 2),
        "annual_saving_yuan": round(annual_saving, 2),
        "payback_years": round(payback, 2) if payback is not None else None,
    }


def _month_emissions(db: Session, year: int, month: int) -> dict[str, dict]:
    """聚合某月各建筑的碳排放(kgCO2e)与用电/夜间电量(kWh)。"""
    factors = carbon_service.load_factors(db)
    result: dict[str, dict] = {}
    stmt = select(EnergyRecord).where(EnergyRecord.year == year, EnergyRecord.month == month)
    for r in db.scalars(stmt):
        row = result.setdefault(
            r.building,
            {"emission": 0.0, "electricity_kwh": 0.0, "night_electricity_kwh": 0.0},
        )
        row["emission"] += carbon_service.calc_emissions(r, factors)["total_emission"]
        row["electricity_kwh"] += r.electricity_kwh
        row["night_electricity_kwh"] += r.night_electricity_kwh
    return result


def diagnose_buildings(db: Session) -> list[dict]:
    """逐建筑诊断：本月 vs 上月碳排放环比 + 夜间用电占比。"""
    # 全库最新月份视为"本月"
    latest = db.execute(
        select(EnergyRecord.year, EnergyRecord.month)
        .order_by(EnergyRecord.year.desc(), EnergyRecord.month.desc())
        .limit(1)
    ).first()
    if latest is None:
        return []
    cur_y, cur_m = latest
    last_y, last_m = prev_month(cur_y, cur_m)

    cur = _month_emissions(db, cur_y, cur_m)
    last = _month_emissions(db, last_y, last_m)
    buildings = sorted(set(cur) | set(last))

    rows: list[dict] = []
    for b in buildings:
        c, p = cur.get(b), last.get(b)
        if not c or not p or p["emission"] <= 0:
            rows.append({
                "building": b, "current_month": f"{cur_y:04d}-{cur_m:02d}",
                "last_month": f"{last_y:04d}-{last_m:02d}",
                "current_emission_kg": round(c["emission"], 2) if c else None,
                "last_emission_kg": round(p["emission"], 2) if p else None,
                "mom_change_pct": None, "night_ratio_pct": None,
                "status": "数据不足",
                "message": f"{b} 缺少 {cur_y:04d}-{cur_m:02d} / {last_y:04d}-{last_m:02d} 连续两月数据，暂无法诊断",
            })
            continue

        mom = (c["emission"] - p["emission"]) / p["emission"] * 100
        night_ratio = (
            c["night_electricity_kwh"] / c["electricity_kwh"] * 100
            if c["electricity_kwh"] > 0 else None
        )
        if mom > MOM_THRESHOLD_PCT and night_ratio is not None and night_ratio > NIGHT_RATIO_THRESHOLD_PCT:
            status = "异常"
            message = f"{b} 本月超标{mom:.1f}%，主要原因为下班后空调未关"
        else:
            status = "正常"
            night_text = f"，夜间用电占比{night_ratio:.1f}%" if night_ratio is not None else ""
            message = f"{b} 本月环比{'+' if mom >= 0 else ''}{mom:.1f}%{night_text}，运行正常"

        rows.append({
            "building": b, "current_month": f"{cur_y:04d}-{cur_m:02d}",
            "last_month": f"{last_y:04d}-{last_m:02d}",
            "current_emission_kg": round(c["emission"], 2),
            "last_emission_kg": round(p["emission"], 2),
            "mom_change_pct": round(mom, 2),
            "night_ratio_pct": round(night_ratio, 2) if night_ratio is not None else None,
            "status": status,
            "message": message,
        })
    return rows
