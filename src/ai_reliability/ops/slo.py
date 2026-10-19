from dataclasses import dataclass

@dataclass(frozen=True)
class SLO:
    availability_target: float
    p95_latency_ms_target: float

def error_budget_fraction(availability_target: float) -> float:
    if not 0 < availability_target <= 1:
        raise ValueError("availability_target must be in (0, 1].")
    return 1.0 - availability_target
