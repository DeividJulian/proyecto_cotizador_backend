from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SimulateRequest(_message.Message):
    __slots__ = ("quote_id", "runs", "samples")
    QUOTE_ID_FIELD_NUMBER: _ClassVar[int]
    RUNS_FIELD_NUMBER: _ClassVar[int]
    SAMPLES_FIELD_NUMBER: _ClassVar[int]
    quote_id: int
    runs: int
    samples: int
    def __init__(self, quote_id: _Optional[int] = ..., runs: _Optional[int] = ..., samples: _Optional[int] = ...) -> None: ...

class SimulateEvent(_message.Message):
    __slots__ = ("progress", "result")
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    progress: Progress
    result: SimulationResult
    def __init__(self, progress: _Optional[_Union[Progress, _Mapping]] = ..., result: _Optional[_Union[SimulationResult, _Mapping]] = ...) -> None: ...

class Progress(_message.Message):
    __slots__ = ("done", "total")
    DONE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    done: int
    total: int
    def __init__(self, done: _Optional[int] = ..., total: _Optional[int] = ...) -> None: ...

class HistogramBin(_message.Message):
    __slots__ = ("start", "end", "count", "over_plan")
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    OVER_PLAN_FIELD_NUMBER: _ClassVar[int]
    start: float
    end: float
    count: int
    over_plan: bool
    def __init__(self, start: _Optional[float] = ..., end: _Optional[float] = ..., count: _Optional[int] = ..., over_plan: _Optional[bool] = ...) -> None: ...

class SimulationResult(_message.Message):
    __slots__ = ("runs", "planned_hours", "mean", "p10", "p50", "p80", "p90", "prob_over_plan", "price_p50", "price_p80", "price_p90", "histogram", "samples", "elapsed_ms")
    RUNS_FIELD_NUMBER: _ClassVar[int]
    PLANNED_HOURS_FIELD_NUMBER: _ClassVar[int]
    MEAN_FIELD_NUMBER: _ClassVar[int]
    P10_FIELD_NUMBER: _ClassVar[int]
    P50_FIELD_NUMBER: _ClassVar[int]
    P80_FIELD_NUMBER: _ClassVar[int]
    P90_FIELD_NUMBER: _ClassVar[int]
    PROB_OVER_PLAN_FIELD_NUMBER: _ClassVar[int]
    PRICE_P50_FIELD_NUMBER: _ClassVar[int]
    PRICE_P80_FIELD_NUMBER: _ClassVar[int]
    PRICE_P90_FIELD_NUMBER: _ClassVar[int]
    HISTOGRAM_FIELD_NUMBER: _ClassVar[int]
    SAMPLES_FIELD_NUMBER: _ClassVar[int]
    ELAPSED_MS_FIELD_NUMBER: _ClassVar[int]
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
    histogram: _containers.RepeatedCompositeFieldContainer[HistogramBin]
    samples: _containers.RepeatedScalarFieldContainer[float]
    elapsed_ms: int
    def __init__(self, runs: _Optional[int] = ..., planned_hours: _Optional[float] = ..., mean: _Optional[float] = ..., p10: _Optional[float] = ..., p50: _Optional[float] = ..., p80: _Optional[float] = ..., p90: _Optional[float] = ..., prob_over_plan: _Optional[float] = ..., price_p50: _Optional[int] = ..., price_p80: _Optional[int] = ..., price_p90: _Optional[int] = ..., histogram: _Optional[_Iterable[_Union[HistogramBin, _Mapping]]] = ..., samples: _Optional[_Iterable[float]] = ..., elapsed_ms: _Optional[int] = ...) -> None: ...
