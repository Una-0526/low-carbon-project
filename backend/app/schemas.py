from datetime import datetime

from pydantic import BaseModel, Field


class CarbonActivityCreate(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    role: str = Field(pattern="^(student|teacher)$")
    activity_type: str = Field(min_length=1, max_length=30)
    carbon_saved_kg: float = Field(ge=0)
    description: str | None = Field(default=None, max_length=200)


class CarbonActivityOut(CarbonActivityCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    total_records: int
    total_carbon_saved_kg: float
    carbon_saved_by_role: dict[str, float]
    carbon_saved_by_type: dict[str, float]
