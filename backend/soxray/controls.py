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

CONTROLS = {
    "ITGC-001": itgc_001
}
