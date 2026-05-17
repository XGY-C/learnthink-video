from app.agents.validator import FixValidator


def test_same_issue_detection():
    validator = FixValidator()
    a = {
        "issueId": "ISSUE_A",
        "stage": "runtime",
        "errorType": "ValueError",
        "rootCauseLabel": "invalid_run_time",
        "normalizedMessage": "run_time <= 0",
        "signature": "abc",
    }
    b = {
        "issueId": "ISSUE_B",
        "stage": "runtime",
        "errorType": "ValueError",
        "rootCauseLabel": "invalid_run_time",
        "normalizedMessage": "run_time <= 0",
        "signature": "abc",
    }
    assert validator.is_same_issue(a, b)
