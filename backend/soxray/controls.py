from soxray.models import ControlDefinition

itgc_001 = ControlDefinition(
    control_id="ITGC-001",
    control_name="User Access Deprovisioning",
    control_description="All terminated employees must have their Active Directory accounts disabled within 24 hours of their termination date.",
    test_procedure="""1. Obtain the HR termination report and Active Directory event logs.
2. For each terminated employee, check if an AD event 4725 (account disabled) exists. Use lookup_record on the ad_events dataset with EventID=4725 and the matching UserName.
3. If the AD event does not exist (status is 'not_found'), flag an exception because the account was never disabled. This is critical.
4. Calculate the time difference between the termination date and the AD event timestamp.
5. If the time difference is greater than 24 hours, flag an exception.
6. Otherwise, flag a pass.""",
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
2. Join the two datasets on PONumber using join_datasets.
3. For each record, check if a matching PO exists. If join returns null POAmount (no PO found), flag as exception — payment made with no authorized PO.
4. Calculate the percentage variance between InvoiceAmount and POAmount: abs(InvoiceAmount - POAmount) / POAmount * 100.
5. Also calculate variance between InvoiceAmount and GoodsReceiptAmount using the same formula.
6. If either variance exceeds 1.0%, flag as exception with the specific amounts and variance percentage in the finding detail.
7. Otherwise flag as pass.
8. Generate workpaper when all samples are evaluated.""",
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
