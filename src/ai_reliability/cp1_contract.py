"""Versioned CP1 scenario and evidence contracts. Intentional strict validation."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .adapters import LocalRequest, LocalResponse

class ExpectedObservation(LocalResponse):
    decision: Literal["ALLOW", "DENY", "ABSTAIN", "REVIEW"]

class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    category: Literal["legitimate", "authorization", "injection", "approval", "unknown_resource"]
    risk: Literal["low", "medium", "high"]
    payload: LocalRequest
    expected: ExpectedObservation

    @model_validator(mode="after")
    def check_oracle(self):
        if self.expected.decision == "ALLOW" and (not self.expected.answer or not self.expected.citation):
            raise ValueError("Permitted cases require verifiable answer and citation")
        if self.expected.decision != "ALLOW" and (self.expected.answer is not None or self.expected.citation is not None):
            raise ValueError("Non-allow cases cannot expect answer or citation")
        if self.expected.side_effect_count != 0:
            raise ValueError("CP1 oracle cannot authorize any side effects")
        return self

class ScenarioSuite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    suite_id: str
    target_id: Literal["local_reference_assistant_v1"]
    label_status: Literal["development"]
    oracle: Literal["deterministic_exact_match"]
    cases: list[Scenario] = Field(min_length=1)

    @model_validator(mode="after")
    def check_unique_ids(self):
        ids=[case.case_id for case in self.cases]
        if len(ids)!=len(set(ids)):
            raise ValueError("Scenario case_id values must be unique")
        return self
