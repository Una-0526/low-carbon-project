"""模拟数据种子：为校园建筑生成最近 12 个月的能耗记录，用于验证碳核算接口。

生成规则：
- 用电量按「日模拟 → 月汇总」：工作日为基础负荷，周末按比例下降；
  夏季（7、8月）与冬季（12、1月）因制冷/采暖偏高；
  寒暑假（2、7、8月）教学楼 / 图书馆用电明显下降，宿舍、食堂基本不变。
- 食堂：每月同时写入天然气（工作日高于周末，食堂周末开餐少）。
- 公务车：每月写入一条汽油用量（building 字段复用为"公务车"）。

用法（需在 backend 目录下运行，数据库为 backend/lowcarbon.db）：
    python seed_mock_data.py            # energy_records 为空时生成
    python seed_mock_data.py --force    # 清空已有能耗记录后重新生成
"""
import argparse
import calendar
import random
from datetime import date

from app.database import Base, SessionLocal, engine
from app.models import EnergyRecord
from app.schemas import EnergyRecordIn
from app.services import auth_service
from app.services import carbon as carbon_service

TODAY = date.today()
rng = random.Random(42)  # 固定种子，结果可复现

# 季节系数（index = 月份-1）：冬夏制冷 / 采暖高峰
SEASONAL = [1.35, 1.15, 1.00, 0.95, 1.00, 1.15, 1.30, 1.30, 1.10, 1.00, 1.10, 1.30]
# 假期系数：寒暑假教学 / 图书馆用电下降
VACATION = {2: 0.55, 7: 0.60, 8: 0.60}

# 用电建筑：(名称, 工作日日电量kWh, 周末日电量kWh, 是否受寒暑假影响)
ELECTRIC_BUILDINGS = [
    ("教学楼A", 1500, 600, True),
    ("教学楼B", 1300, 520, True),
    ("宿舍楼", 1200, 1140, False),
    ("图书馆", 1000, 500, True),
    ("食堂", 600, 500, False),
]

# 食堂天然气：(工作日 m³/日, 周末 m³/日)
CANTEEN_GAS = (160, 80)
# 公务车：每月汽油基数（L）
VEHICLE_GASOLINE_MONTHLY = 500


def recent_months(n: int = 12) -> list[tuple[int, int]]:
    """最近 n 个月的 (year, month)，按时间升序。"""
    months = []
    y, m = TODAY.year, TODAY.month
    for _ in range(n):
        months.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(months))


def monthly_electricity(year: int, month: int, weekday_kwh: float, weekend_kwh: float,
                        has_vacation: bool) -> float:
    """按日累计月用电量：工作日 / 周末分开，叠加季节、假期与随机波动。"""
    total = 0.0
    days = calendar.monthrange(year, month)[1]
    for d in range(1, days + 1):
        is_weekend = date(year, month, d).weekday() >= 5
        daily = weekend_kwh if is_weekend else weekday_kwh
        daily *= SEASONAL[month - 1]
        if has_vacation and month in VACATION:
            daily *= VACATION[month]
        daily *= rng.uniform(0.9, 1.1)
        total += daily
    return round(total, 1)


def monthly_canteen_gas(year: int, month: int) -> float:
    """食堂月天然气：工作日 / 周末天数分别累计。"""
    days = calendar.monthrange(year, month)[1]
    weekday_days = sum(1 for d in range(1, days + 1) if date(year, month, d).weekday() < 5)
    total = weekday_days * CANTEEN_GAS[0] + (days - weekday_days) * CANTEEN_GAS[1]
    return round(total * rng.uniform(0.9, 1.1), 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成模拟能耗数据")
    parser.add_argument("--force", action="store_true", help="清空已有能耗记录后重新生成")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        # 建表（若数据库为空），并保证账号 / 因子存在，脚本可独立运行
        Base.metadata.create_all(bind=engine)
        auth_service.ensure_demo_users(db)
        carbon_service.ensure_default_factors(db)

        existing = db.query(EnergyRecord.id).count()
        if existing and not args.force:
            print(f"energy_records 已有 {existing} 条数据，如需重新生成请加 --force")
            return
        if existing:
            db.query(EnergyRecord).delete()
            db.commit()
            print(f"已清空原有 {existing} 条能耗记录")

        count = 0
        for year, month in recent_months(12):
            for name, weekday_kwh, weekend_kwh, has_vacation in ELECTRIC_BUILDINGS:
                record_in = EnergyRecordIn(
                    building=name,
                    year=year,
                    month=month,
                    electricity_kwh=monthly_electricity(year, month, weekday_kwh, weekend_kwh, has_vacation),
                    natural_gas_m3=monthly_canteen_gas(year, month) if name == "食堂" else 0,
                )
                carbon_service.create_record(db, record_in)
                count += 1
            carbon_service.create_record(db, EnergyRecordIn(
                building="公务车",
                year=year,
                month=month,
                gasoline_l=round(VEHICLE_GASOLINE_MONTHLY * rng.uniform(0.8, 1.2), 1),
            ))
            count += 1

        print(f"已生成 {count} 条记录（{len(recent_months(12))} 个月：5 栋建筑用电 + 食堂天然气 + 公务车汽油）")
        print("\n各建筑碳核算汇总（kgCO2e）：")
        for row in carbon_service.get_stats(db, "building"):
            print(f"  {row['group']}: 总排放 {row['total_emission']:.1f}，减碳 {row['total_reduction']:.1f}，净排放 {row['net_emission']:.1f}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
