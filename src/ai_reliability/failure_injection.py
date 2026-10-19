from dataclasses import dataclass

@dataclass
class InjectedFailure:
    kind: str
    message: str

def inject(kind: str) -> InjectedFailure:
    supported = {
        "timeout": "Simulated upstream timeout",
        "rate_limit": "Simulated HTTP 429",
        "malformed_json": "Simulated malformed model/tool response",
        "auth_failure": "Simulated authentication failure",
    }
    if kind not in supported:
        raise ValueError(f"Unsupported failure kind: {kind}")
    return InjectedFailure(kind=kind, message=supported[kind])
