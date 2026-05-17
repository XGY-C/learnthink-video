from __future__ import annotations

from pydantic import BaseModel, Field


class IssueFingerprint(BaseModel):
    issue_id: str = Field(alias="issueId")
    stage: str
    error_type: str = Field(alias="errorType")
    root_cause_label: str = Field(alias="rootCauseLabel")
    normalized_message: str = Field(alias="normalizedMessage")
    signature: str
    confidence: float
    evidence_lines: list[str] = Field(default_factory=list, alias="evidenceLines")
    source_file: str | None = Field(default=None, alias="sourceFile")
    line_no: int | None = Field(default=None, alias="lineNo")
    priority: int = 1


class RepairDecision(BaseModel):
    attempt_no: int = Field(alias="attemptNo")
    target_issue_ids: list[str] = Field(default_factory=list, alias="targetIssueIds")
    fix_strategy: str = Field(alias="fixStrategy")
    expected_outcome: str = Field(alias="expectedOutcome")
    patch_summary: list[str] = Field(default_factory=list, alias="patchSummary")


class FixValidationResult(BaseModel):
    target_issue_ids: list[str] = Field(default_factory=list, alias="targetIssueIds")
    resolved_issue_ids: list[str] = Field(default_factory=list, alias="resolvedIssueIds")
    unresolved_issue_ids: list[str] = Field(default_factory=list, alias="unresolvedIssueIds")
    blocked_issue_ids: list[str] = Field(default_factory=list, alias="blockedIssueIds")
    is_effective: bool = Field(alias="isEffective")
    should_learn: bool = Field(alias="shouldLearn")
    reason: str
    candidate_notice: str | None = Field(default=None, alias="candidateNotice")
