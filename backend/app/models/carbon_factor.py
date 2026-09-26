from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CarbonFactor(Base):
    """碳排放 / 减碳因子表，数值可配置（kgCO2e per unit）。"""

    __tablename__ = "carbon_factors"
    __table_args__ = (UniqueConstraint("factor_key", name="uq_factor_key"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    factor_key: Mapped[str] = mapped_column(String(50))  # 见 services/carbon.py DEFAULT_FACTORS
    name: Mapped[str] = mapped_column(String(50))
    unit: Mapped[str] = mapped_column(String(20))  # 因子单位，如 kWh / m3 / L
    factor: Mapped[float] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(String(200), default=None)
