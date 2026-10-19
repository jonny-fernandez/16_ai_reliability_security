"""Strict CP2 development-gate, provenance and governance contracts."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class GatePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    policy_id: str = Field(min_length=3)
    min_cases: int = Field(ge=1)
    required_categories: dict[str, int]
    required_decisions: dict[Literal["ALLOW","DENY","ABSTAIN","REVIEW"], int]
    warn_exact_below: float = Field(ge=0,le=1)
    block_exact_below: float = Field(ge=0,le=1)
    block_false_block_at: float = Field(gt=0,le=1)
    block_on_any_false_allow: bool = True
    block_on_any_side_effect: bool = True
    block_on_high_risk_mismatch: bool = True
    block_on_missing_governance: bool = True

    @model_validator(mode="after")
    def check_thresholds(self):
        if self.block_exact_below > self.warn_exact_below:
            raise ValueError("block_exact_below cannot exceed warn_exact_below")
        if not self.required_categories or not self.required_decisions:
            raise ValueError("coverage requirements cannot be empty")
        if any(n<1 for n in (*self.required_categories.values(),*self.required_decisions.values())):
            raise ValueError("required case counts must be positive")
        if not all((self.block_on_any_false_allow,self.block_on_any_side_effect,
                    self.block_on_high_risk_mismatch,self.block_on_missing_governance)):
            raise ValueError("CP2 development policy cannot disable critical safety checks")
        return self

class GovernanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    owner_role: str = Field(min_length=2)
    review_status: Literal["DEVELOPMENT_UNAPPROVED"]
    system_id: Literal["local_reference_assistant_v1"]
    system_version: str = Field(min_length=1)
    intended_use: str = Field(min_length=10)
    prohibited_use: list[str] = Field(min_length=1)
    dataset_name: str = Field(min_length=3)
    dataset_version: str = Field(min_length=1)
    dataset_provenance: str = Field(min_length=10)
    limitations: list[str] = Field(min_length=1)
    sensitivity: Literal["SYNTHETIC_NON_SENSITIVE"]
    evaluation_unit: Literal["stateless_reference_invocation"]
    oracle: Literal["deterministic_exact_match"]
    subgroup_policy: Literal["scenario_categories_only_not_demographic_fairness"]
    candidate_approval: Literal[False]
