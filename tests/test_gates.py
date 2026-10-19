from ai_reliability.gates import release_gate
from ai_reliability.failure_injection import inject

def test_gate_pass():
    assert release_gate(0.98, 0.0) == "PASS"

def test_gate_warn():
    assert release_gate(0.92, 0.0) == "WARN"

def test_security_blocks():
    assert release_gate(0.99, 0.01) == "BLOCK"

def test_failure_injection():
    assert inject("timeout").kind == "timeout"
