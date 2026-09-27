from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EnergyRecord(Base):
    """建筑能耗记录：一条 = 某建筑某月的水电气等用量，用于碳核算。"""

    __tablename__ = "energy_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    building: Mapped[str] = mapped_column(String(50), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer)  # 1-12
    semester: Mapped[str] = mapped_column(String(20), index=True)  # 如 2025-2026-1，创建时按 year/month 推导

    # 排放活动数据
    electricity_kwh: Mapped[float] = mapped_column(Float, default=0.0)   # 市电用电量 → Scope2
    night_electricity_kwh: Mapped[float] = mapped_column(Float, default=0.0)  # 其中夜间(22:00-6:00)电量，用于异常诊断
    natural_gas_m3: Mapped[float] = mapped_column(Float, default=0.0)    # 天然气 → Scope1
    gasoline_l: Mapped[float] = mapped_column(Float, default=0.0)        # 汽油 → Scope1

    # 减碳活动数据（替代电网电量）
    pv_kwh: Mapped[float] = mapped_column(Float, default=0.0)      # 光伏发电量
    storage_kwh: Mapped[float] = mapped_column(Float, default=0.0)  # 储能削峰电量
    saving_kwh: Mapped[float] = mapped_column(Float, default=0.0)   # 节能措施节电量
