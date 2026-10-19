def release_gate(task_success_rate: float, security_violation_rate: float) -> str:
    if security_violation_rate > 0:
        return "BLOCK"
    if task_success_rate < 0.90:
        return "BLOCK"
    if task_success_rate < 0.95:
        return "WARN"
    return "PASS"
