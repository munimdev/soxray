from typing import Any, Literal
from pydantic import BaseModel, Field

class ControlDefinition(BaseModel):
    control_id: str
    control_name: str
    control_description: str
    test_procedure: str
    frequency: str
    control_type: str
    threshold_rules: dict[str, Any] = Field(default_factory=dict)

class EvidenceFile(BaseModel):
    filename: str
    file_type: str
    parsed_content: Any
    evidence_type: str

class EvidencePackage(BaseModel):
    control_id: str
    files: list[EvidenceFile]

class TestFinding(BaseModel):
    sample_id: str
    sample_identifier: str
    result: Literal["PASS", "EXCEPTION", "INCONCLUSIVE"]
    evidence_citations: list[str]
    finding_detail: str
    control_owner_response: str | None = None

class WorkpaperOutput(BaseModel):
    control: ControlDefinition
    total_samples: int
    exceptions: int
    findings: list[TestFinding]
    conclusion: str
