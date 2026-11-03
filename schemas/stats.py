from pydantic import BaseModel


class StatusCount(BaseModel):
    draft: int
    sent: int
    accepted: int
    rejected: int


class TopModule(BaseModel):
    module: str
    count: int


class Stats(BaseModel):
    total_quotes: int
    by_status: StatusCount
    close_rate_pct: float | None  # null while no quote was accepted or rejected
    average_ticket: int
    accepted_value: int
    negotiating_value: int
    hours_by_role: dict[str, float]
    top_modules: list[TopModule]


class SeedSummary(BaseModel):
    quotes: int


class SeedResult(BaseModel):
    message: str
    summary: SeedSummary
