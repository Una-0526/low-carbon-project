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
