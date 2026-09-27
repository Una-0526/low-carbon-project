from datetime import datetime

from pydantic import BaseModel, Field


# ---------- 认证 ----------

class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class UserOut(BaseModel):
    username: str
    role: str
    class_name: str | None = None
    dormitory: str | None = None

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: UserOut


# ---------- 低碳行为 ----------

class CarbonActivityCreate(BaseModel):
    """提交记录时 username / role 一律取自登录态，不接受前端传入。"""

    activity_type: str = Field(min_length=1, max_length=30)
    carbon_saved_kg: float = Field(ge=0)
    description: str | None = Field(default=None, max_length=200)


class CarbonActivityOut(BaseModel):
    id: int
    username: str
    role: str
    activity_type: str
    carbon_saved_kg: float
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    total_records: int
    total_carbon_saved_kg: float
    carbon_saved_by_role: dict[str, float]
    carbon_saved_by_type: dict[str, float]


# ---------- 碳核算 ----------

class CarbonFactorOut(BaseModel):
    factor_key: str
    name: str
    unit: str
    factor: float
    description: str | None = None

    model_config = {"from_attributes": True}


class CarbonFactorIn(BaseModel):
    factor: float = Field(ge=0)


class EnergyRecordIn(BaseModel):
    building: str = Field(min_length=1, max_length=50)
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    electricity_kwh: float = Field(default=0, ge=0)   # 市电 → Scope2
    night_electricity_kwh: float = Field(default=0, ge=0)  # 夜间(22:00-6:00)电量，应 ≤ 用电量
    natural_gas_m3: float = Field(default=0, ge=0)    # 天然气 → Scope1
    gasoline_l: float = Field(default=0, ge=0)        # 汽油 → Scope1
    pv_kwh: float = Field(default=0, ge=0)            # 光伏发电（减碳）
    storage_kwh: float = Field(default=0, ge=0)       # 储能削峰（减碳）
    saving_kwh: float = Field(default=0, ge=0)        # 节能量（减碳）


class EmissionOut(BaseModel):
    scope1: float
    scope2: float
    total_emission: float
    total_reduction: float
    net_emission: float


class EnergyRecordOut(EnergyRecordIn):
    id: int
    semester: str
    emissions: EmissionOut


class StatRowOut(BaseModel):
    group: str
    scope1: float
    scope2: float
    total_emission: float
    total_reduction: float
    net_emission: float
    record_count: int


class CarbonStatsOut(BaseModel):
    group_by: str
    unit: str = "kgCO2e"
    rows: list[StatRowOut]


# ---------- 异常诊断 / 方案库 ----------

class SolutionIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=20)  # 光伏 / 储能 / 节能改造 / 峰谷策略
    annual_electricity_kwh: float = Field(ge=0)   # 年覆盖电量
    investment: float = Field(ge=0)               # 投资额（元）
    electricity_price: float = Field(ge=0)        # 折算电价（元/kWh）
    factor: float | None = Field(default=None, ge=0)  # 减碳因子，缺省用电网因子
    description: str | None = Field(default=None, max_length=200)


class SolutionOut(SolutionIn):
    id: int
    annual_carbon_reduction_kg: float  # 年减碳量 = 电量 × 因子
    annual_saving_yuan: float          # 年省电费 = 电量 × 电价
    payback_years: float | None        # 回收期 = 投资 ÷ 年省电费


class BuildingDiagnosisOut(BaseModel):
    building: str
    current_month: str | None      # 如 2026-09
    last_month: str | None
    current_emission_kg: float | None
    last_emission_kg: float | None
    mom_change_pct: float | None   # 环比变化 %
    night_ratio_pct: float | None  # 夜间用电占比 %
    status: str                    # 异常 / 正常 / 数据不足
    message: str                   # 诊断结论


# ---------- 绿色打卡 / 积分 ----------

class CheckinOut(BaseModel):
    id: int
    user_id: int
    username: str
    task_type: str
    photo_path: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    status: str
    ai_flagged: bool
    ai_flags: list[str] = []
    points_awarded: int
    review_reason: str | None = None
    note: str | None = None
    created_at: datetime


class RejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class ApproveResultOut(BaseModel):
    checkin: CheckinOut
    streak: int
    bonus: int


class CheckinSummaryOut(BaseModel):
    total_points: int
    streak_days: int


class PointTransactionOut(BaseModel):
    id: int
    points: int
    reason: str
    checkin_id: int | None = None
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PointSummaryOut(BaseModel):
    total_points: int
    transactions: list[PointTransactionOut]


# ---------- 学生碳诊断 ----------

class CategoryStatOut(BaseModel):
    category: str          # 出行 / 饮食 / 节约用电
    week_count: int
    week_carbon_kg: float


class MonthlyReportOut(BaseModel):
    month: str                     # 如 2026-09
    carbon_kg: float               # 本月减碳总量
    checkin_count: int
    class_name: str | None
    rank: int | None               # 班级排名
    class_size: int | None
    percentile: int | None         # 超过班级同学的百分比


class MyDiagnosisOut(BaseModel):
    week_carbon_kg: float
    week_count: int
    month_carbon_kg: float
    month_count: int
    total_points: int
    streak_days: int
    categories: list[CategoryStatOut]
    advice: list[str]
    monthly_report: MonthlyReportOut


# ---------- 积分商城 ----------

class RewardItemOut(BaseModel):
    id: int
    name: str
    category: str
    points_cost: int
    stock: int
    is_active: bool
    description: str | None = None

    model_config = {"from_attributes": True}


class RewardItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=20)  # 食堂 / 超市 / 文具
    points_cost: int = Field(ge=1)
    stock: int = Field(ge=0)
    is_active: bool = True
    description: str | None = Field(default=None, max_length=200)


class RedemptionOut(BaseModel):
    id: int
    user_id: int
    username: str
    item_id: int
    item_name: str
    points_cost: int
    status: str
    created_at: datetime
    fulfilled_at: datetime | None = None


class RedeemResultOut(BaseModel):
    redemption: RedemptionOut
    remaining_points: int
