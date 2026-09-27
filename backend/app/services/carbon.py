"""碳核算服务：Scope1 / Scope2 排放与减碳核算，排放因子可配置。

核算口径（单位 kgCO2e）：
- Scope2 排放 = 用电量(kWh) × 电网排放因子
- Scope1 排放 = 天然气(m³) × 天然气因子 + 汽油(L) × 汽油因子
- 减碳量     = 光伏电量 × 光伏因子 + 储能削峰电量 × 储能因子 + 节电量 × 节能因子
- 净排放     = Scope1 + Scope2 − 减碳量
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CarbonFactor, EnergyRecord
from app.schemas import EnergyRecordIn

# 默认因子（carbon_factors 表为空时写入，表中数值可随时修改生效）
DEFAULT_FACTORS: list[dict] = [
    {"factor_key": "grid_electricity", "name": "电网排放因子", "unit": "kWh", "factor": 0.5703,
     "description": "Scope2：每度市电的碳排放"},
    {"factor_key": "natural_gas", "name": "天然气排放因子", "unit": "m3", "factor": 2.162,
     "description": "Scope1：每立方米天然气的碳排放"},
    {"factor_key": "gasoline", "name": "汽油排放因子", "unit": "L", "factor": 2.30,
     "description": "Scope1：每升汽油的碳排放"},
    {"factor_key": "pv_reduction", "name": "光伏减碳因子", "unit": "kWh", "factor": 0.5703,
     "description": "每度光伏发电替代电网电量的减碳量"},
    {"factor_key": "storage_reduction", "name": "储能减碳因子", "unit": "kWh", "factor": 0.5703,
     "description": "每度储能削峰电量替代电网电量的减碳量"},
    {"factor_key": "saving_reduction", "name": "节能减碳因子", "unit": "kWh", "factor": 0.5703,
     "description": "每度节电量替代电网电量的减碳量"},
]

# 学期划分：9月-次年1月为第一学期，2-8月为第二学期（含暑期）
SEMESTER_FIRST = "1"
SEMESTER_SECOND = "2"


def semester_of(year: int, month: int) -> str:
    """由年月推导所属学期，格式：起始年-结束年-学期号，如 2025-2026-1。"""
    if month >= 9:
        return f"{year}-{year + 1}-{SEMESTER_FIRST}"
    if month == 1:
        return f"{year - 1}-{year}-{SEMESTER_FIRST}"
    return f"{year - 1}-{year}-{SEMESTER_SECOND}"


def ensure_default_factors(db: Session) -> None:
    """carbon_factors 表为空时写入默认因子。"""
    if db.scalar(select(CarbonFactor.id).limit(1)) is not None:
        return
    db.add_all([CarbonFactor(**item) for item in DEFAULT_FACTORS])
    db.commit()


def load_factors(db: Session) -> dict[str, float]:
    """加载全部因子，返回 {factor_key: factor}。"""
    return {f.factor_key: f.factor for f in db.scalars(select(CarbonFactor))}


def calc_emissions(record: EnergyRecord, factors: dict[str, float]) -> dict:
    """核算单条记录：返回 Scope1 / Scope2 / 总排放 / 减碳量 / 净排放（kgCO2e）。"""
    scope2 = record.electricity_kwh * factors.get("grid_electricity", 0.0)
    scope1 = (
        record.natural_gas_m3 * factors.get("natural_gas", 0.0)
        + record.gasoline_l * factors.get("gasoline", 0.0)
    )
    reduction = (
        record.pv_kwh * factors.get("pv_reduction", 0.0)
        + record.storage_kwh * factors.get("storage_reduction", 0.0)
        + record.saving_kwh * factors.get("saving_reduction", 0.0)
    )
    return {
        "scope1": round(scope1, 4),
        "scope2": round(scope2, 4),
        "total_emission": round(scope1 + scope2, 4),
        "total_reduction": round(reduction, 4),
        "net_emission": round(scope1 + scope2 - reduction, 4),
    }


def create_record(db: Session, data: EnergyRecordIn) -> tuple[EnergyRecord, dict]:
    """新建一条建筑能耗记录，学期自动推导。"""
    record = EnergyRecord(
        building=data.building,
        year=data.year,
        month=data.month,
        semester=semester_of(data.year, data.month),
        electricity_kwh=data.electricity_kwh,
        night_electricity_kwh=data.night_electricity_kwh,
        natural_gas_m3=data.natural_gas_m3,
        gasoline_l=data.gasoline_l,
        pv_kwh=data.pv_kwh,
        storage_kwh=data.storage_kwh,
        saving_kwh=data.saving_kwh,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, calc_emissions(record, load_factors(db))


def list_records(
    db: Session,
    year: int | None = None,
    building: str | None = None,
    semester: str | None = None,
) -> list[tuple[EnergyRecord, dict]]:
    """查询记录并逐条核算。"""
    stmt = (
        select(EnergyRecord)
        .order_by(EnergyRecord.year, EnergyRecord.month, EnergyRecord.building)
    )
    if year:
        stmt = stmt.where(EnergyRecord.year == year)
    if building:
        stmt = stmt.where(EnergyRecord.building == building)
    if semester:
        stmt = stmt.where(EnergyRecord.semester == semester)
    factors = load_factors(db)
    return [(r, calc_emissions(r, factors)) for r in db.scalars(stmt)]


def get_stats(
    db: Session,
    group_by: str,  # building | month | semester
    year: int | None = None,
    building: str | None = None,
    semester: str | None = None,
) -> list[dict]:
    """按建筑 / 按月 / 按学期聚合，返回碳排放与减碳数据。"""
    stmt = select(EnergyRecord)
    if year:
        stmt = stmt.where(EnergyRecord.year == year)
    if building:
        stmt = stmt.where(EnergyRecord.building == building)
    if semester:
        stmt = stmt.where(EnergyRecord.semester == semester)

    factors = load_factors(db)
    agg: dict[str, dict] = {}

    for r in db.scalars(stmt):
        e = calc_emissions(r, factors)
        if group_by == "building":
            key = r.building
        elif group_by == "month":
            key = f"{r.year:04d}-{r.month:02d}"
        elif group_by == "semester":
            key = r.semester
        else:
            raise ValueError(f"不支持的统计维度: {group_by}")

        row = agg.setdefault(
            key,
            {"group": key, "scope1": 0.0, "scope2": 0.0, "total_emission": 0.0,
             "total_reduction": 0.0, "net_emission": 0.0, "record_count": 0},
        )
        row["scope1"] += e["scope1"]
        row["scope2"] += e["scope2"]
        row["total_emission"] += e["total_emission"]
        row["total_reduction"] += e["total_reduction"]
        row["net_emission"] += e["net_emission"]
        row["record_count"] += 1

    rows = [
        {k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}
        for row in agg.values()
    ]
    rows.sort(key=lambda r: r["group"])
    return rows
