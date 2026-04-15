from typing import TypedDict, Annotated, Sequence, Any
import operator
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from soxray.tools import (
    load_evidence as load_evidence_fn,
    join_datasets as join_datasets_fn,
    calculate_deltas as calculate_deltas_fn,
    lookup_records as lookup_records_fn,
    flag_findings_batch as flag_findings_batch_fn,
    generate_workpaper_from_context,
)


@tool
def load_evidence(filename: str) -> dict:
    """Loads a CSV evidence file into a List of dicts."""
    return load_evidence_fn(filename).model_dump()


@tool
def join_datasets(df1: list, df2: list, join_key: str) -> list:
    """Joins two datasets (lists of dicts) on a common key."""
    return join_datasets_fn(df1, df2, join_key)


@tool
def calculate_deltas(
    timestamps_first: list[str],
    timestamps_second: list[str],
    unit: str = "hours",
) -> list[float]:
    """Calculates time differences for many pairs in one call. Lists must be same length. Returns hours (or days/seconds if unit set). Use -1.0 for invalid/missing pairs."""
    return calculate_deltas_fn(timestamps_first, timestamps_second, unit)


@tool
def lookup_records(dataset: list, key: str, values: list[Any]) -> list[dict]:
    """Looks up multiple records in a dataset in a single call. Returns a list of records or structured not found results aligned with the input values."""
    return lookup_records_fn(dataset, key, values)


@tool
def flag_findings_batch(findings: list[dict]) -> list[dict]:
    """Records many findings in one call. Each item: sample_id, sample_identifier, result ('PASS' or 'EXCEPTION'), evidence_citations (list of strings), and for EXCEPTION optionally finding_detail. Prefer this over calling flag_pass/flag_exception in a loop when you have multiple samples."""
    return flag_findings_batch_fn(findings)


@tool
def generate_workpaper(
    total_samples: int,
    exceptions: int,
    conclusion: str,
) -> str:
    """Generates the workpaper document using the previously recorded findings and current control context. Call this as the VERY LAST tool when you have finished testing all records to summarize findings. IMPORTANT: Call this tool only once, as the final step."""
    return generate_workpaper_from_context(total_samples, exceptions, conclusion)


tools = [
    load_evidence,
    join_datasets,
    calculate_deltas,
    lookup_records,
    flag_findings_batch,
    generate_workpaper,
]


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def get_agent_executor():
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)

    SYS_PROMPT = """You are a SOX ITGC Testing Agent.
You will be provided with a ControlDefinition and an EvidencePackage describing the files you have available.
You must execute the testing procedure described in the control strictly using the available tools.

Steps you normally take:
1. Load the evidence files using `load_evidence`.
2. When you need information from multiple datasets, prefer using `join_datasets` once or `lookup_records` for batch lookups. Do not call record-level lookup tools repeatedly in a loop when a single join or batch lookup will do.
3. When you need time differences for many rows (for example, termination date vs event time), use `calculate_deltas` once with two lists of timestamps instead of calling a per-row delta function in a loop.
4. When you have evaluated all samples, record results in one batch: call `flag_findings_batch` with a list of findings (each with sample_id, sample_identifier, result, evidence_citations, and for EXCEPTION optionally finding_detail). Do not call per-sample flag tools in a loop for many samples.
5. IMPORTANT: `lookup_records` may return a 'not_found' dictionary. That is a control exception when the rule requires the record to exist (for example, account disable event). Do not treat missing records as logic errors.
6. ONLY AFTER all findings are recorded, call `generate_workpaper` once with total_samples, exceptions, and conclusion.

CRITICAL RULES FOR `generate_workpaper`:
- DO NOT call `generate_workpaper` in the same response as `flag_findings_batch`. Wait for that tool response first.
- Call `generate_workpaper` EXACTLY ONCE for the entire test. Never call it in a loop or multiple times.
- When you call `generate_workpaper`, you MUST provide all of the following named arguments:
  - `total_samples`: the total number of samples you actually tested (integer).
  - `exceptions`: the total number of exceptions you identified (integer).
  - `conclusion`: a short narrative conclusion string.
- The control metadata and detailed findings will be pulled automatically from the prior `flag_findings_batch` tool calls and internal context.
- Finish your response after generating the workpaper.

Example call (structure only):
`generate_workpaper(total_samples=10, exceptions=2, conclusion="Control failed due to 2 exceptions out of 10 samples (20%).")`.
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
    
    def after_tools(state: AgentState):
        last_message = state["messages"][-1]
        # if the last tool executed was generate_workpaper, terminate graph
        if getattr(last_message, "name", "") == "generate_workpaper":
            return END
        return "agent"

    workflow.add_conditional_edges("tools", after_tools, {"agent": "agent", END: END})

    cw = workflow.compile()
    return cw
