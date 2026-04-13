from typing import TypedDict, Annotated, Sequence, Any
import operator
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from soxray.models import ControlDefinition, WorkpaperOutput
from soxray.tools import (
    load_evidence as load_evidence_fn,
    join_datasets as join_datasets_fn,
    calculate_delta as calculate_delta_fn,
    lookup_record as lookup_record_fn,
    flag_exception as flag_exception_fn,
    flag_pass as flag_pass_fn,
    write_workpaper as write_workpaper_fn,
)


@tool
def load_evidence(filename: str) -> dict:
    return load_evidence_fn(filename).model_dump()


@tool
def join_datasets(df1: list, df2: list, join_key: str) -> list:
    return join_datasets_fn(df1, df2, join_key)


@tool
def calculate_delta(timestamp1: str, timestamp2: str, unit: str = "hours") -> float:
    return calculate_delta_fn(timestamp1, timestamp2, unit)


@tool
def lookup_record(dataset: list, key: str, value: Any) -> dict:
    return lookup_record_fn(dataset, key, value)


@tool
def flag_exception(
    sample_id: str, sample_identifier: str, finding_detail: str, citations: list[str]
) -> dict:
    return flag_exception_fn(
        sample_id, sample_identifier, finding_detail, citations
    ).model_dump()


@tool
def flag_pass(sample_id: str, sample_identifier: str, citations: list[str]) -> dict:
    return flag_pass_fn(sample_id, sample_identifier, citations).model_dump()


@tool
def generate_workpaper(
    control_dict: dict,
    total_samples: int,
    exceptions: int,
    findings: list[dict],
    conclusion: str,
) -> str:
    control = ControlDefinition(**control_dict)
    from soxray.models import TestFinding

    parsed_findings = [TestFinding(**f) for f in findings]
    output = WorkpaperOutput(
        control=control,
        total_samples=total_samples,
        exceptions=exceptions,
        findings=parsed_findings,
        conclusion=conclusion,
    )
    return write_workpaper_fn(output)


tools = [
    load_evidence,
    join_datasets,
    calculate_delta,
    lookup_record,
    flag_exception,
    flag_pass,
    generate_workpaper,
]


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def get_agent_executor():
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    llm_with_tools = llm.bind_tools(tools)

    SYS_PROMPT = """You are a SOX ITGC Testing Agent.
You will be provided with a ControlDefinition and an EvidencePackage describing the files you have available.
You must execute the testing procedure described in the control strictly using the available tools.
    
Steps you normally take:
1. Load the evidence files using `load_evidence`.
2. Perform necessary data joins if needed using `join_datasets`.
3. Iterate through each sample based on the Control threshold rules.
   - You may use `calculate_delta` or `lookup_record`.
   - IMPORTANT: `lookup_record` might return a 'not_found' dictionary if the record doesn't exist. This is a critical finding if the rule requires the record to exist (e.g., account disable event). Do not assume missing records are errors in your logic; they are control exceptions.
4. Call `flag_exception` or `flag_pass` for EVERY sample evaluated based on the rules.
5. After all samples are evaluated, call `generate_workpaper` with the summarized findings and your overall conclusion. Finish your response after generating the workpaper.
"""

    def call_model(state: AgentState):
        messages = [SystemMessage(content=SYS_PROMPT)] + list(state["messages"])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]

        if not getattr(last_message, "tool_calls", None):
            return END

        return "tools"

    workflow = StateGraph(AgentState)
    tool_node = ToolNode(tools)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    workflow.add_edge("tools", "agent")

    cw = workflow.compile()
    return cw
