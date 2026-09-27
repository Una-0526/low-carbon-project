"""碳中和路径模拟：三情景分段模型逐年排放推演（2026-2060）。

模型口径（分段模型）：
- 基线排放 = 最近 12 个月能耗记录的碳排放合计（Scope1 + Scope2），基线年 = 当前年份
- 基准·保守情景：2026-2030 每年 +1.5% 自然增长，2030 年达峰后平台期保持不变
  → 达峰 2030 年，2060 年仍维持峰值水平，无法实现碳中和
- 节能改造·现实推荐情景：2026 年 +1.5%、2027 年 +0.5%，2028 年达峰；此后每年线性减排
  达峰排放 / 32（2028→2060 恰好 32 年），2060 年降至 0 → 2060 年按期中和
- 全面光伏·理想激进情景：2026 年即达峰（基线排放），此后每年线性减排 基线 / 20，
  2046 年降至 0 → 提前 14 年中和
"""
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EnergyRecord
from app.services import carbon as carbon_service

TARGET_PEAK_YEAR = 2030      # 国家碳达峰目标线
TARGET_NEUTRAL_YEAR = 2060   # 国家碳中和目标线

BASE_YEAR = date.today().year          # 2026
END_YEAR = TARGET_NEUTRAL_YEAR         # 2060
BASELINE_GROWTH = 0.015                # 保守情景（及节能改造首年）的年增长率
EFFICIENCY_GROWTH_LATE = 0.005         # 节能改造情景次年的增长率
EFFICIENCY_PEAK_YEAR = BASE_YEAR + 2   # 节能改造 2028 年达峰
SOLAR_NEUTRAL_YEAR = BASE_YEAR + 20    # 全面光伏 2046 年中和（提前 14 年）


def base_emission_kg(db: Session) -> float:
    """基线排放：最近 12 个月记录的碳排放合计（kgCO2e）。"""
    months = db.execute(
        select(EnergyRecord.year, EnergyRecord.month)
        .distinct()
        .order_by(EnergyRecord.year.desc(), EnergyRecord.month.desc())
        .limit(12)
    ).all()
    if not months:
        return 0.0
    factors = carbon_service.load_factors(db)
    total = 0.0
    for year, month in months:
        stmt = select(EnergyRecord).where(EnergyRecord.year == year, EnergyRecord.month == month)
        for r in db.scalars(stmt):
            total += carbon_service.calc_emissions(r, factors)["total_emission"]
    return total


def _series(values_by_year: dict[int, float]) -> list[dict]:
    """按 2026-2060 逐年输出，缺省年份视为 0。"""
    return [
        {"year": y, "emission_t": round(values_by_year.get(y, 0.0), 2)}
        for y in range(BASE_YEAR, END_YEAR + 1)
    ]


def simulate(db: Session) -> dict:
    """三情景分段模拟，返回各情景逐年序列、达峰/中和年份与结论。"""
    base_kg = base_emission_kg(db)
    if base_kg <= 0:
        return {"base_year": BASE_YEAR, "base_emission_t": 0.0, "scenarios": [],
                "conclusion": "暂无能耗数据，请先生成或录入能耗记录"}
    base_t = base_kg / 1000

    scenarios: list[dict] = []

    # 1 基准·保守情景：2026-2030 每年 +1.5%，2030 达峰后平台期不变
    values = {y: base_t * (1 + BASELINE_GROWTH) ** (y - BASE_YEAR)
              for y in range(BASE_YEAR, TARGET_PEAK_YEAR + 1)}
    peak_t = values[TARGET_PEAK_YEAR]
    for y in range(TARGET_PEAK_YEAR, END_YEAR + 1):
        values[y] = peak_t
    scenarios.append({
        "key": "baseline", "name": "基准情景", "tag": "保守",
        "description": "维持现状管理措施，排放随校园规模自然增长后趋平",
        "peak_year": TARGET_PEAK_YEAR, "peak_emission_t": round(peak_t, 2),
        "neutral_year": None,
        "neutral_note": "无法实现碳中和",
        "annual_decline_t": 0.0,
        "emission_2060_t": round(peak_t, 2),
        "series": _series(values),
    })

    # 2 节能改造·现实推荐情景：+1.5%、+0.5% 后 2028 达峰，线性减排至 2060 归零
    peak_eff_t = base_t * (1 + BASELINE_GROWTH) * (1 + EFFICIENCY_GROWTH_LATE)
    values = {BASE_YEAR: base_t, BASE_YEAR + 1: base_t * (1 + BASELINE_GROWTH)}
    for y in range(EFFICIENCY_PEAK_YEAR, END_YEAR + 1):
        values[y] = max(0.0, peak_eff_t * (1 - (y - EFFICIENCY_PEAK_YEAR) / (END_YEAR - EFFICIENCY_PEAK_YEAR)))
    neutral_eff = next((y for y in range(EFFICIENCY_PEAK_YEAR, END_YEAR + 1) if values[y] <= 0), None)
    scenarios.append({
        "key": "efficiency", "name": "节能改造情景", "tag": "现实推荐",
        "description": "LED 照明 + 空调变频等节能改造全面实施，达峰后逐年线性减排",
        "peak_year": EFFICIENCY_PEAK_YEAR, "peak_emission_t": round(peak_eff_t, 2),
        "neutral_year": neutral_eff,
        "neutral_note": f"{neutral_eff} 年按期中和",
        "annual_decline_t": round(peak_eff_t / (END_YEAR - EFFICIENCY_PEAK_YEAR), 2),
        "emission_2060_t": 0.0,
        "series": _series(values),
    })

    # 3 全面光伏·理想激进情景：2026 即达峰，每年线性减排 基线/20，2046 归零
    values = {y: max(0.0, base_t * (1 - (y - BASE_YEAR) / (SOLAR_NEUTRAL_YEAR - BASE_YEAR)))
              for y in range(BASE_YEAR, END_YEAR + 1)}
    scenarios.append({
        "key": "solar", "name": "全面光伏情景", "tag": "理想激进",
        "description": "校园电力全面光伏化并配套储能，以最大力度线性减排",
        "peak_year": BASE_YEAR, "peak_emission_t": round(base_t, 2),
        "neutral_year": SOLAR_NEUTRAL_YEAR,
        "neutral_note": f"{SOLAR_NEUTRAL_YEAR} 年提前 {END_YEAR - SOLAR_NEUTRAL_YEAR} 年中和",
        "annual_decline_t": round(base_t / (SOLAR_NEUTRAL_YEAR - BASE_YEAR), 2),
        "emission_2060_t": 0.0,
        "series": _series(values),
    })

    return {
        "base_year": BASE_YEAR,
        "base_emission_t": round(base_t, 2),
        "target_peak_year": TARGET_PEAK_YEAR,
        "target_neutral_year": TARGET_NEUTRAL_YEAR,
        "scenarios": scenarios,
        "conclusion": "现实推荐情景可2060年按期中和；激进情景提前14年但投资规模更大；保守情景将无法实现双碳目标。",
        "note": "模型口径：分段模型——基线排放取最近 12 个月碳排放合计；保守情景年增 1.5% 后持平，"
                "节能改造 2028 年达峰后线性减排，全面光伏 2026 年达峰后线性减排",
    }
