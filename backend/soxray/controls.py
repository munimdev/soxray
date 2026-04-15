from soxray.models import ControlDefinition

itgc_001 = ControlDefinition(
    control_id="ITGC-001",
    control_name="User Access Deprovisioning",
    control_description="All terminated employees must have their Active Directory accounts disabled within 24 hours of their termination date.",
    test_procedure="""1. Load the HR termination report and AD event logs with load_evidence.
2. Join once: use join_datasets(hr_data, ad_data, "UserName"). Filter the joined result to rows where EventID=4725 (account disabled), or join then filter in memory so each terminated user has at most one 4725 event row.
3. For rows with no 4725 event (missing or not_found), the account was never disabled: record as EXCEPTION.
4. Compute all time differences in one call: use calculate_deltas(list of TerminationDate values, list of EventTime values, "hours") for the joined rows.
5. For each row: if delta > 24 hours or missing, record EXCEPTION; else record PASS.
6. Record all results in one call: use flag_findings_batch with a list of {sample_id, sample_identifier, result, evidence_citations, finding_detail for exceptions}.
7. Call generate_workpaper with total_samples, exceptions, and conclusion.""",
    frequency="Quarterly",
    control_type="ITGC",
    threshold_rules={
        "max_hours": 24,
        "required_event": 4725,
        "join_key": "UserName",
        "termination_timestamp_col": "TerminationDate",
        "event_timestamp_col": "EventTime"
    }
)

bpc_001 = ControlDefinition(
    control_id="BPC-001",
    control_name="Invoice 3-Way Match",
    control_description="All vendor invoices must be approved for payment only when the invoice amount, purchase order amount, and goods receipt quantity × unit price agree within a 1% tolerance. Discrepancies must be flagged before payment is processed.",
    test_procedure="""1. Load data/invoices.csv and data/purchase_orders.csv using load_evidence.
2. Join the two datasets on PONumber using join_datasets so each invoice row has its PO and goods receipt data.
3. In memory, for every joined row compute:
   - variance_po = abs(InvoiceAmount - POAmount) / POAmount * 100
   - variance_gr = abs(InvoiceAmount - GoodsReceiptAmount) / GoodsReceiptAmount * 100
4. Build a list of findings with one entry per invoice:
   - If POAmount is null (no PO found), set result = EXCEPTION with finding_detail explaining that payment was made without an authorized PO.
   - Else if either variance_po or variance_gr exceeds 1.0, set result = EXCEPTION with finding_detail including the relevant amounts and variance percentages.
   - Otherwise set result = PASS.
5. Call flag_findings_batch once with the full list of findings (each item containing sample_id, sample_identifier, result, evidence_citations, and for exceptions the finding_detail).
6. Call generate_workpaper with total_samples, exceptions, and conclusion once all samples are evaluated.""",
    frequency="Semi-Annual",
    control_type="BPC",
    threshold_rules={
        "tolerance_pct": 1.0,
        "join_key": "PONumber",
        "invoice_amount_col": "InvoiceAmount",
        "po_amount_col": "POAmount",
        "goods_receipt_col": "GoodsReceiptAmount"
    }
)

CONTROLS = {
    "ITGC-001": itgc_001,
    "BPC-001": bpc_001
}
