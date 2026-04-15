import pandas as pd
from datetime import datetime, timedelta
import os
import random

def generate_synthetic_data():
    os.makedirs("data", exist_ok=True)
    
    base_date = datetime(2026, 3, 1, 9, 0)
    
    terminations = []
    ad_events = []
    
    for i in range(1, 11):
        emp_id = f"EMP{i:03d}"
        username = f"user.{i}"
        
        term_date = base_date + timedelta(days=i)
        
        terminations.append({
            "EmpID": emp_id,
            "UserName": username,
            "TerminationDate": term_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Department": random.choice(["Engineering", "Sales", "HR", "Marketing"])
        })
        
        if i <= 8:
            # 8 Clean: Disabled within 24 hours (e.g., 2 hours later)
            event_time = term_date + timedelta(hours=2)
            ad_events.append({
                "EventID": 4725,
                "UserName": username,
                "EventTime": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                "PerformedBy": "admin.svc"
            })
        elif i == 9:
            # 1 Exception: Gap > 24h (e.g., 72 hours later)
            event_time = term_date + timedelta(hours=72)
            ad_events.append({
                "EventID": 4725,
                "UserName": username,
                "EventTime": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                "PerformedBy": "admin.svc"
            })
        elif i == 10:
            # 1 Exception: No disable event at all (MIA)
            # Maybe they have a different event like a login (4624) instead, or nothing
            ad_events.append({
                "EventID": 4624, # Not the disable event
                "UserName": username,
                "EventTime": (term_date + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "PerformedBy": username
            })
            
    # Add some noise to AD events
    for i in range(5):
        ad_events.append({
            "EventID": random.choice([4624, 4625, 4728]),
            "UserName": f"other.user.{i}",
            "EventTime": (base_date + timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S"),
            "PerformedBy": "system"
        })

    term_df = pd.DataFrame(terminations)
    term_df.to_csv("data/workday_terminations.csv", index=False)
    
    ad_df = pd.DataFrame(ad_events)
    ad_df.to_csv("data/ad_events.csv", index=False)
    
    print(f"Generated {len(term_df)} termination records in data/workday_terminations.csv")
    print(f"Generated {len(ad_df)} AD event records in data/ad_events.csv")

    # 2. Generate 10 Invoices and POs for BPC-001
    invoices = []
    purchase_orders = []
    
    vendors = ["Acme Corp", "TechFlow", "Global Supplies", "Consulting Pro"]
    
    for i in range(1, 11):
        inv_id = f"INV-{i:03d}"
        po_number = f"PO-2026-{i:03d}"
        vendor = random.choice(vendors)
        base_amount = round(random.uniform(5000, 50000), 2)
        inv_date = (base_date - timedelta(days=random.randint(1, 15))).strftime("%Y-%m-%d")
        
        if i <= 7:
            # Clean: exact matches
            invoices.append({"InvoiceID": inv_id, "PONumber": po_number, "VendorName": vendor, "InvoiceAmount": base_amount, "InvoiceDate": inv_date})
            purchase_orders.append({"PONumber": po_number, "VendorName": vendor, "POAmount": base_amount, "GoodsReceiptAmount": base_amount, "ApprovedBy": f"manager.{i}"})
        elif i == 8:
            # Overbilling: Invoice 15% higher
            inv_amount = round(base_amount * 1.15, 2)
            invoices.append({"InvoiceID": inv_id, "PONumber": po_number, "VendorName": vendor, "InvoiceAmount": inv_amount, "InvoiceDate": inv_date})
            purchase_orders.append({"PONumber": po_number, "VendorName": vendor, "POAmount": base_amount, "GoodsReceiptAmount": base_amount, "ApprovedBy": f"manager.{i}"})
        elif i == 9:
            # Missing goods: GoodsReceipt is 60%
            good_amount = round(base_amount * 0.60, 2)
            invoices.append({"InvoiceID": inv_id, "PONumber": po_number, "VendorName": vendor, "InvoiceAmount": base_amount, "InvoiceDate": inv_date})
            purchase_orders.append({"PONumber": po_number, "VendorName": vendor, "POAmount": base_amount, "GoodsReceiptAmount": good_amount, "ApprovedBy": f"manager.{i}"})
        elif i == 10:
            # No matching PO
            invoices.append({"InvoiceID": inv_id, "PONumber": po_number, "VendorName": vendor, "InvoiceAmount": base_amount, "InvoiceDate": inv_date})
            # Purchase order does NOT exist

    inv_df = pd.DataFrame(invoices)
    inv_df.to_csv("data/invoices.csv", index=False)
    
    po_df = pd.DataFrame(purchase_orders)
    po_df.to_csv("data/purchase_orders.csv", index=False)
    
    print(f"Generated {len(inv_df)} records in data/invoices.csv")
    print(f"Generated {len(po_df)} records in data/purchase_orders.csv")

if __name__ == "__main__":
    generate_synthetic_data()
