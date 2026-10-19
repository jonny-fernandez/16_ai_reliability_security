"""Local reference system and a generic target adapter contract.

The adapter models an isolated system under test. It never reaches a network,
never executes untrusted instructions, and never persists consequential writes.
"""
from __future__ import annotations
from typing import Protocol, Any
from pydantic import BaseModel, ConfigDict, Field

class TargetAdapter(Protocol):
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]: ...

class LocalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str
    resource_id: str
    scopes: list[str] = Field(default_factory=list)
    untrusted_text: str = Field(default="", max_length=2000)

class LocalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str
    reason_code: str
    answer: str | None = None
    citation: str | None = None
    side_effect_count: int = Field(default=0, ge=0)

class LocalReferenceAdapter:
    """A deterministic, scoped knowledge assistant + write-approval simulator.

    Answers are retrieved verbatim from built-in synthetic docs. The payload's
    untrusted_text is non-authoritative and is NEVER used to decide permission.
    """
    target_id = "local_reference_assistant_v1"
    _docs = {
        "public_handbook": (
            "Synthetic help desk hours are Monday through Friday, 9 AM to 5 PM.",
            "public:read",
        ),
        "internal_runbook": (
            "Synthetic escalation tickets route to the internal operations queue.",
            "internal:read",
        ),
    }

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = LocalRequest.model_validate(payload)
        scopes = set(req.scopes)
        if req.operation == "lookup":
            doc = self._docs.get(req.resource_id)
            if doc is None:
                result = LocalResponse(decision="ABSTAIN", reason_code="UNKNOWN_RESOURCE")
            elif doc[1] not in scopes:
                result = LocalResponse(decision="DENY", reason_code="MISSING_READ_SCOPE")
            else:
                result = LocalResponse(
                    decision="ALLOW", reason_code="AUTHORIZED_GROUNDED_LOOKUP",
                    answer=doc[0], citation=f"synthetic://{req.resource_id}",
                )
        elif req.operation == "propose_write":
            if "record:write" not in scopes:
                result = LocalResponse(decision="DENY", reason_code="MISSING_WRITE_SCOPE")
            else:
                result = LocalResponse(decision="REVIEW", reason_code="HUMAN_APPROVAL_REQUIRED")
        else:
            result = LocalResponse(decision="DENY", reason_code="UNSUPPORTED_OPERATION")
        return result.model_dump(mode="json")
