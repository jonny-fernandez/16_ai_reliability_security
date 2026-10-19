import pytest

from ai_reliability.governance.fairness import absolute_group_gap
from ai_reliability.ops.slo import error_budget_fraction
from ai_reliability.ops.incidents import incident_severity

def test_group_gap():
    assert absolute_group_gap(0.82, 0.75) == pytest.approx(0.07)

def test_error_budget():
    assert round(error_budget_fraction(0.999), 3) == 0.001

def test_security_incident_is_sev1():
    assert incident_severity(False, True, False) == "SEV1"
