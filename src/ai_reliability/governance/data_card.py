from pydantic import BaseModel, Field

class DataCardRecord(BaseModel):
    dataset_name: str
    dataset_version: str
    source_description: str
    sensitive_fields: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
