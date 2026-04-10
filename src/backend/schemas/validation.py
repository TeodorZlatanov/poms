from pydantic import BaseModel

from models.enums import IssueSeverity, IssueTagType, ValidationCheckType, ValidationResult


class IssueTagResult(BaseModel):
    tag: IssueTagType
    severity: IssueSeverity
    description: str


class ValidationCheckResult(BaseModel):
    check_type: ValidationCheckType
    result: ValidationResult
    details: dict
    tags: list[IssueTagResult] = []
