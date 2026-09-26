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
