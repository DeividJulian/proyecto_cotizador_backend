from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Role = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]


class RateCreate(BaseModel):
    role: Role
    hourly_rate: int = Field(gt=0, le=2_000_000)


class RateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    hourly_rate: int


class MarketRate(BaseModel):
    role: str
    hourly_rate: int
