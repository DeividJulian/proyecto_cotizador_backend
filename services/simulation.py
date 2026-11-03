"""Monte Carlo simulation of a saved quote. Both the REST endpoint and the gRPC (Connect) service use this generator.

Each module has three PERT estimates (optimistic, most likely, pessimistic). Instead of adding only the average,
thousands of possible projects are drawn with the Beta-PERT distribution (numpy, vectorized) to measure how many hours,
and at what price, cover 50 %, 80 % or 90 % of the cases. Same method as the front's Web Worker
(cotizador-front/src/app/core/workers/simulation.logic.ts), which keeps working offline.
"""
import time
from collections.abc import Iterator

import numpy as np

from models.quote import Quote

MIN_RUNS = 1_000
# Render's free plan has a fraction of a CPU: 200.000 projects take about a second there
MAX_RUNS = 200_000
MAX_SAMPLES = 50_000
STEPS = 10  # progress events per simulation
BINS = 30
SEED = 2026  # same quote and runs -> same result


class SimulationUnavailable(Exception):
    """The quote cannot be simulated yet (it has no price). The message is shown to the user."""


class InvalidSimulation(ValueError):
    """Runs or samples out of range. The message is shown to the user."""


def _percentile(sorted_totals: np.ndarray, fraction: float) -> float:
    """Same rule as the front: the value at floor(fraction * n) of the sorted totals."""
    return float(sorted_totals[min(len(sorted_totals) - 1, int(fraction * len(sorted_totals)))])


def simulate(quote: Quote, runs: int, samples: int = 0) -> Iterator[dict]:
    """Yields {"progress": {...}} STEPS times and, at the end, {"result": {...}}. Nothing is saved."""
    if not quote.items or not quote.total:
        raise SimulationUnavailable("Analiza la cotización antes de simularla")
    if not MIN_RUNS <= runs <= MAX_RUNS:
        raise InvalidSimulation(f"Las simulaciones deben estar entre {MIN_RUNS:,} y {MAX_RUNS:,}".replace(",", "."))
    if not 0 <= samples <= min(MAX_SAMPLES, runs):
        raise InvalidSimulation(f"Las muestras deben estar entre 0 y {min(MAX_SAMPLES, runs):,}".replace(",", "."))

    started = time.perf_counter()
    o = np.array([i.hours_optimistic for i in quote.items], dtype=float)
    m = np.array([i.hours_likely for i in quote.items], dtype=float)
    p = np.array([i.hours_pessimistic for i in quote.items], dtype=float)
    spread = p - o
    flat = spread <= 0  # a module without range always takes its most likely hours
    safe = np.where(flat, 1.0, spread)
    alpha = np.where(flat, 1.0, 1 + 4 * (m - o) / safe)
    beta = np.where(flat, 1.0, 1 + 4 * (p - m) / safe)

    planned = float((quote.estimate or {}).get("hours_expected") or sum(i.hours_expected for i in quote.items))
    price_per_hour = quote.total / planned if planned > 0 else 0.0

    rng = np.random.default_rng(SEED)
    totals = np.empty(runs)
    sizes = np.full(STEPS, runs // STEPS)
    sizes[: runs % STEPS] += 1
    done = 0
    for size in sizes:
        draws = rng.beta(alpha, beta, size=(int(size), len(o)))
        totals[done : done + size] = np.where(flat, m, o + spread * draws).sum(axis=1)
        done += int(size)
        yield {"progress": {"done": done, "total": runs}}

    over = float((totals > planned).mean())
    sample = totals[:samples].round(1).tolist()
    totals.sort()
    counts, edges = np.histogram(totals, bins=BINS)
    p50, p80, p90 = (_percentile(totals, f) for f in (0.5, 0.8, 0.9))
    yield {
        "result": {
            "runs": runs,
            "planned_hours": round(planned, 1),
            "mean": round(float(totals.mean()), 1),
            "p10": round(_percentile(totals, 0.1), 1),
            "p50": round(p50, 1),
            "p80": round(p80, 1),
            "p90": round(p90, 1),
            "prob_over_plan": round(over, 4),
            "price_p50": round(p50 * price_per_hour),
            "price_p80": round(p80 * price_per_hour),
            "price_p90": round(p90 * price_per_hour),
            "histogram": [
                {"start": round(float(lo), 1), "end": round(float(hi), 1), "count": int(c), "over_plan": bool(lo >= planned)}
                for lo, hi, c in zip(edges[:-1], edges[1:], counts)
            ],
            "samples": sample,
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        }
    }


def run(quote: Quote, runs: int, samples: int = 0) -> dict:
    """The whole simulation at once (REST): only the final result."""
    result = {}
    for event in simulate(quote, runs, samples):
        result = event.get("result", result)
    return result
