from pydantic import BaseModel, Field

class ModelCardRecord(BaseModel):
    model_name: str
    model_version: str
    intended_use: str
    primary_metric: str
    approved: bool = False
    limitations: list[str] = Field(default_factory=list)
