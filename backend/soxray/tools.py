import pandas as pd
from pathlib import Path
from typing import Any, cast
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

from soxray.models import EvidenceFile, TestFinding, WorkpaperOutput, ControlDefinition


def _escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_current_control: ControlDefinition | None = None
_findings_buffer: list[TestFinding] = []


def set_current_control(control: ControlDefinition) -> None:
    global _current_control, _findings_buffer
    _current_control = control
    _findings_buffer = []


def _record_finding(finding: TestFinding) -> None:
    _findings_buffer.append(finding)


def _get_current_context() -> tuple[ControlDefinition, list[TestFinding]]:
    if _current_control is None:
        raise ValueError("Current control is not set for workpaper generation.")
    return _current_control, list(_findings_buffer)


def load_evidence(filename: str) -> EvidenceFile:
    df = pd.read_csv(filename)
    parsed = df.replace({pd.NA: None}).to_dict(orient="records")
    
    evidence_type = "unknown"
    if "termination" in filename.lower():
        evidence_type = "HR_report"
    elif "ad_events" in filename.lower():
        evidence_type = "AD_log"
        
    return EvidenceFile(
        filename=filename,
        file_type="csv",
        parsed_content=parsed,
        evidence_type=evidence_type
    )

def join_datasets(df1: list[dict[str, Any]], df2: list[dict[str, Any]], join_key: str) -> list[dict[str, Any]]:
    pdf1 = pd.DataFrame(df1)
    pdf2 = pd.DataFrame(df2)
    
    if pdf1.empty or pdf2.empty:
        return []
        
    merged = pd.merge(pdf1, pdf2, on=join_key, how="left")
    return cast(list[dict[str, Any]], merged.replace({pd.NA: None}).to_dict(orient="records"))

def calculate_delta(timestamp1: Any, timestamp2: Any, unit: str = "hours") -> float:
    if pd.isna(timestamp1) or pd.isna(timestamp2) or not timestamp1 or not timestamp2:
        return -1.0
        
    t1 = pd.to_datetime(timestamp1)
    t2 = pd.to_datetime(timestamp2)
    
    delta = t2 - t1
    
    if unit == "hours":
        return delta.total_seconds() / 3600.0
    elif unit == "days":
        return delta.total_seconds() / (3600.0 * 24.0)
    return delta.total_seconds()


def calculate_deltas(
    timestamps_first: list[Any],
    timestamps_second: list[Any],
    unit: str = "hours",
) -> list[float]:
    if len(timestamps_first) != len(timestamps_second):
        raise ValueError("timestamps_first and timestamps_second must have the same length")
    result: list[float] = []
    for t1, t2 in zip(timestamps_first, timestamps_second):
        result.append(calculate_delta(t1, t2, unit))
    return result


def lookup_record(dataset: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    for record in dataset:
        if record.get(key) == value:
            return record
    
    return {"status": "not_found", "message": f"No record found with {key}={value}"}


def lookup_records(
    dataset: list[dict[str, Any]],
    key: str,
    values: list[Any],
) -> list[dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for record in dataset:
        record_key = record.get(key)
        if record_key is not None and record_key not in index:
            index[record_key] = record

    results: list[dict[str, Any]] = []
    for value in values:
        if value in index:
            results.append(index[value])
        else:
            results.append(
                {
                    "status": "not_found",
                    "message": f"No record found with {key}={value}",
                    "key": key,
                    "value": value,
                }
            )
    return results

def flag_exception(sample_id: str, sample_identifier: str, finding_detail: str, citations: list[str]) -> TestFinding:
    finding = TestFinding(
        sample_id=sample_id,
        sample_identifier=sample_identifier,
        result="EXCEPTION",
        evidence_citations=citations,
        finding_detail=finding_detail
    )
    _record_finding(finding)
    return finding

def flag_pass(sample_id: str, sample_identifier: str, citations: list[str]) -> TestFinding:
    finding = TestFinding(
        sample_id=sample_id,
        sample_identifier=sample_identifier,
        result="PASS",
        evidence_citations=citations,
        finding_detail="Sample passed testing without exceptions."
    )
    _record_finding(finding)
    return finding


def flag_findings_batch(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in findings:
        result_raw = f.get("result", "PASS")
        result_type = str(result_raw).upper() if result_raw else "PASS"
        if result_type not in ("PASS", "EXCEPTION", "INCONCLUSIVE"):
            result_type = "INCONCLUSIVE"
        detail = f.get("finding_detail")
        if result_type == "EXCEPTION" and not detail:
            detail = "Exception identified."
        elif result_type == "PASS":
            detail = detail or "Sample passed testing without exceptions."
        else:
            detail = detail or "Inconclusive."
        finding = TestFinding(
            sample_id=str(f["sample_id"]),
            sample_identifier=str(f["sample_identifier"]),
            result=result_type,
            evidence_citations=list(f.get("evidence_citations", [])),
            finding_detail=detail,
        )
        _record_finding(finding)
        out.append(finding.model_dump())
    return out


def generate_workpaper_from_context(total_samples: int, exceptions: int, conclusion: str) -> str:
    control, findings = _get_current_context()

    actual_total = len(findings)
    total = total_samples if total_samples > 0 else actual_total

    actual_exceptions = sum(1 for f in findings if f.result == "EXCEPTION")
    exc_count = exceptions if exceptions > 0 else actual_exceptions

    output = WorkpaperOutput(
        control=control,
        total_samples=total,
        exceptions=exc_count,
        findings=findings,
        conclusion=conclusion,
    )
    return write_workpaper(output)

def write_workpaper(output: WorkpaperOutput) -> str:
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    filename = out_dir / f"workpaper_{output.control.control_id.lower()}.pdf"

    doc = SimpleDocTemplate(
        str(filename),
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="CenterTitle",
        parent=styles["Heading1"],
        alignment=1,
    )

    story: list[Any] = []

    story.append(
        Paragraph(
            _escape_xml(f"SOX Workpaper: {output.control.control_id}"),
            title_style,
        )
    )
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            _escape_xml(f"Control Name: {output.control.control_name}"),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 12))

    header_data = [
        ["Test Date", datetime.now().strftime("%Y-%m-%d")],
        ["Preparer", "soxray.ai Automated Agent"],
        ["Control Type / Freq", f"{output.control.control_type} / {output.control.frequency}"],
    ]
    header_table = Table(header_data, colWidths=[2 * inch, 4 * inch])
    header_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Control Description", styles["Heading1"]))
    story.append(Paragraph(_escape_xml(output.control.control_description), styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Test Procedure", styles["Heading1"]))
    procedure_source = (
        output.control.workpaper_test_summary
        if output.control.workpaper_test_summary
        else output.control.test_procedure
    )
    procedure_text = _escape_xml(procedure_source).replace("\n", "<br/>")
    story.append(Paragraph(procedure_text, styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Results Summary", styles["Heading1"]))
    summary_text = (
        f"Total Samples Tested: {output.total_samples}<br/>"
        f"Total Exceptions Identified: {output.exceptions}<br/>"
        f"Exception Rate: {(output.exceptions / max(1, output.total_samples)) * 100:.2f}%"
    )
    story.append(Paragraph(summary_text, styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Sample Testing Selection & Results", styles["Heading1"]))
    cell_style = ParagraphStyle(
        name="TableCell",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    )
    sample_data: list[list[Any]] = [
        ["Sample ID", "Identifier", "Result", Paragraph("Evidence Citations", cell_style)],
    ]
    for finding in output.findings:
        citations_text = ", ".join(finding.evidence_citations)
        sample_data.append([
            finding.sample_id,
            finding.sample_identifier,
            finding.result,
            Paragraph(_escape_xml(citations_text), cell_style),
        ])
    evidence_col_width = 3.5 * inch
    sample_table = Table(
        sample_data,
        colWidths=[1.2 * inch, 1.5 * inch, 1 * inch, evidence_col_width],
    )
    sample_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ])
    )
    story.append(sample_table)
    story.append(Spacer(1, 16))

    if output.exceptions > 0:
        story.append(Paragraph("Exception Details", styles["Heading1"]))
        for finding in output.findings:
            if finding.result == "EXCEPTION":
                story.append(
                    Paragraph(
                        f"<b>Sample {_escape_xml(finding.sample_id)} ({_escape_xml(finding.sample_identifier)}):</b> "
                        f"{_escape_xml(finding.finding_detail)}",
                        styles["Normal"],
                    )
                )
                story.append(
                    Paragraph(
                        "<i>Management Response: </i>"
                        f"{_escape_xml(finding.control_owner_response or 'Pending Input')}",
                        styles["Normal"],
                    )
                )
        story.append(Spacer(1, 12))

    story.append(Paragraph("Conclusion", styles["Heading1"]))
    story.append(
        Paragraph(f"<b>{_escape_xml(output.conclusion)}</b>", styles["Normal"])
    )

    doc.build(story)
    return str(filename)
