from enum import Enum
from pydantic import BaseModel


class Severity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Finding(BaseModel):
    file: str
    description: str
    severity: Severity
    suggestion: str


class ReviewResult(BaseModel):
    logic_issues: list[Finding]
    security_issues: list[Finding]
    code_quality: list[Finding]
    performance_issues: list[Finding]
    test_coverage: list[Finding]
    summary: str