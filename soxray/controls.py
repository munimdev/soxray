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
    },
    workpaper_test_summary=(
        "1. Obtain the HR termination report and the log of user account activity.\n"
        "2. Identify all employees who left the company during the period under review.\n"
        "3. For each terminated employee, look for evidence that their system access "
        "was disabled.\n"
        "4. Compare the termination date to the date the account was disabled to "
        "confirm this occurred within 24 hours.\n"
        "5. Conclude on whether access for terminated employees was removed on a "
        "timely basis and summarize any exceptions identified."
    ),
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
   - If POAmount is null (no PO found), set result = EXCEPTION with a short, plain-language finding_detail explaining that payment was made without an authorized PO and why this is a control failure (for example, \"Invoice was paid without a matching approved purchase order.\").
   - Else if either variance_po or variance_gr exceeds 1.0, set result = EXCEPTION with a brief narrative finding_detail that describes the variance in business terms (for example, \"Invoice amount exceeded the purchase order by 15%, which is above the 1% tolerance.\").
   - Otherwise set result = PASS with a concise note that the invoice matched the related purchase order and goods receipt within the 1% tolerance.
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
    },
    workpaper_test_summary=(
        "1. Obtain a report of vendor invoices and the related purchase orders and goods receipts "
        "for the period under review.\n"
        "2. For each sampled invoice, compare the invoice amount to the approved purchase order "
        "and the quantity received to confirm that the invoice is supported.\n"
        "3. Identify any invoices where the billed amount or quantity does not agree to the "
        "underlying purchase order or goods received within a 1% tolerance.\n"
        "4. Treat invoices without an approved purchase order, or with differences greater than "
        "the 1% tolerance, as exceptions.\n"
        "5. Conclude on whether the 3-way match control is operating effectively based on the "
        "number and nature of exceptions identified."
    ),
)

CONTROLS = {
    "ITGC-001": itgc_001,
    "BPC-001": bpc_001
}
