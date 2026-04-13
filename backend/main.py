import os
import argparse
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from soxray.agent import get_agent_executor
from soxray.controls import CONTROLS
from soxray.models import EvidencePackage, EvidenceFile
from soxray.tools import load_evidence

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="soxray.ai SOX ITGC Testing Execution")
    parser.add_argument("control_id", type=str, help="ID of the control to test (e.g., ITGC-001)")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must be set in the environment or .env file.")

    if args.control_id not in CONTROLS:
        raise ValueError(f"Control ID {args.control_id} not found in defined controls.")
        
    control = CONTROLS[args.control_id]
    print(f"Starting test execution for {control.control_id}: {control.control_name}")

    # simplified for this demo, manually routing files
    evidence_package = EvidencePackage(
        control_id=control.control_id,
        files=[
            EvidenceFile(filename="data/workday_terminations.csv", file_type="csv", parsed_content=None, evidence_type="HR_report"),
            EvidenceFile(filename="data/ad_events.csv", file_type="csv", parsed_content=None, evidence_type="AD_log")
        ]
    )

    agent = get_agent_executor()

    prompt = f"""
Please execute testing for the following control.

CONTROL DEFINITION:
{control.model_dump_json(indent=2)}

EVIDENCE PACKAGE AVAILABLE:
{', '.join([f.filename for f in evidence_package.files])}

Start by loading the evidence using the `load_evidence` tool, then execute the control's `test_procedure` step by step using the tools.
Ensure you loop through every required record in the HR report.
When finished, aggregate all your exceptions and passes, and output the final workpaper using `generate_workpaper`.
It is crucial that you test ALL {len(load_evidence("data/workday_terminations.csv").parsed_content)} records. 
"""

    initial_state = {"messages": [HumanMessage(content=prompt)]}
    
    print("Agent is analyzing evidence and executing control procedure...\n")
    for event in agent.stream(initial_state):
        for key, value in event.items():
            if key == "agent":
                message = value["messages"][0]
                if message.tool_calls:
                    print(f"Agent called tools: {[tc['name'] for tc in message.tool_calls]}")
                else:
                    print(f"\nAgent Message:\n{message.content}")
            elif key == "tools":
                pass
                
    print(f"\nTesting complete. Workpaper saved to output/workpaper_{args.control_id.lower()}.docx")

if __name__ == "__main__":
    main()
