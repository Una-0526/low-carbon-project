from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Solution(Base):
    """节能减碳方案库：一条 = 一个可选方案及其测算参数。

    计算口径（读取时动态计算）：
    - 年减碳量(kgCO2e) = 年覆盖电量(kWh) × 减碳因子（未指定时取电网因子）
    - 年省电费(元)     = 年覆盖电量(kWh) × 电价(元/kWh，可为峰谷差价等折算单价)
    - 回收期(年)       = 投资(元) ÷ 年省电费(元)
    """

    __tablename__ = "solutions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    category: Mapped[str] = mapped_column(String(20))  # 光伏 / 储能 / 节能改造 / 峰谷策略
    annual_electricity_kwh: Mapped[float] = mapped_column(Float)  # 年覆盖电量
    investment: Mapped[float] = mapped_column(Float)              # 投资额（元）
    electricity_price: Mapped[float] = mapped_column(Float)       # 折算电价（元/kWh）
    factor: Mapped[float | None] = mapped_column(Float, default=None)  # 减碳因子，None 用电网因子
    description: Mapped[str | None] = mapped_column(String(200), default=None)
