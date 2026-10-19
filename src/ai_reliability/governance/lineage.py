from dataclasses import dataclass

@dataclass(frozen=True)
class LineageRecord:
    dataset_version: str
    feature_version: str
    model_version: str
    code_version: str
