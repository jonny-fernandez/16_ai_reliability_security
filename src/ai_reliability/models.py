from pydantic import BaseModel, Field

class EvalCase(BaseModel):
    case_id: str
    category: str
    input: dict
    expected: dict = Field(default_factory=dict)

class EvalResult(BaseModel):
    case_id: str
    passed: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    findings: list[str] = Field(default_factory=list)
