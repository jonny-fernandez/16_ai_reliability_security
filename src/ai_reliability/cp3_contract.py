"""Frozen CP3 operational scenario and local simulated-SLO policy contracts."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Fault = Literal['ok', 'timeout', 'rate_limit', 'malformed_json', 'auth_failure']
Status = Literal['SUCCESS','RECOVERED','REPLAYED','FAILED_CLOSED','DEGRADED_ABSTAIN','CIRCUIT_OPEN']

class OperationalCase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    case_id: str = Field(pattern=r'^op_[0-9]{2}_[a-z_]+$')
    steps: list[Fault] = Field(min_length=1, max_length=3)
    expected_status: Status
    expected_attempts: int = Field(ge=0,le=3)
    fallback: bool = False
    idempotency_key: str | None = Field(default=None,max_length=60)
    circuit: str | None = Field(default=None,max_length=50)

class OperationalSuite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1.0']
    suite_id: str = Field(min_length=3)
    cases: list[OperationalCase] = Field(min_length=5, max_length=50)

    @model_validator(mode='after')
    def unique_cases(self):
        ids=[case.case_id for case in self.cases]
        if len(ids)!=len(set(ids)):
            raise ValueError('Duplicate operational case IDs')
        if not any(c.expected_status=='REPLAYED' for c in self.cases):
            raise ValueError('Replay coverage required')
        if not any(c.expected_status=='CIRCUIT_OPEN' for c in self.cases):
            raise ValueError('Circuit coverage required')
        if not any(c.expected_status=='DEGRADED_ABSTAIN' for c in self.cases):
            raise ValueError('Fallback coverage required')
        return self

class OperationalPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal['1.0']
    policy_id: str = Field(min_length=3)
    max_attempts: Literal[3]
    breaker_after_failed_requests: Literal[2]
    simulated_availability_target: float = Field(gt=0,le=1)
    simulated_p95_latency_ms_target: float = Field(gt=0)
    benchmark_iterations: int = Field(ge=100,le=2000)
    required_operational_cases: int = Field(ge=5,le=50)
