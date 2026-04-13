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

if __name__ == "__main__":
    generate_synthetic_data()
