from pydantic import BaseModel, Field

from services.simulation import MAX_RUNS, MAX_SAMPLES, MIN_RUNS


class SimulationRequest(BaseModel):
    runs: int = Field(default=100_000, ge=MIN_RUNS, le=MAX_RUNS)
    # Simulated totals to send back, for the REST vs gRPC size comparison
    samples: int = Field(default=0, ge=0, le=MAX_SAMPLES)


class HistogramBin(BaseModel):
    start: float
    end: float
    count: int
    over_plan: bool


class SimulationResult(BaseModel):
    """Same fields as SimulationResult in proto/cotizador/v1/simulation.proto."""
    runs: int
    planned_hours: float
    mean: float
    p10: float
    p50: float
    p80: float
    p90: float
    prob_over_plan: float
    price_p50: int
    price_p80: int
    price_p90: int
    histogram: list[HistogramBin]
    samples: list[float]
    elapsed_ms: int
