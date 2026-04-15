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
    calculate_delta as calculate_delta_fn,
    lookup_record as lookup_record_fn,
    flag_exception as flag_exception_fn,
    flag_pass as flag_pass_fn,
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
def calculate_delta(timestamp1: str, timestamp2: str, unit: str = "hours") -> float:
    """Calculates time difference between two timestamps."""
    return calculate_delta_fn(timestamp1, timestamp2, unit)


@tool
def lookup_record(dataset: list, key: str, value: Any) -> dict:
    """Looks up a record in a dataset. Crucially, if no record is found, returns a structured not found result instead of failing."""
    return lookup_record_fn(dataset, key, value)


@tool
def flag_exception(
    sample_id: str, sample_identifier: str, finding_detail: str, citations: list[str]
) -> dict:
    """Flags an exception for a given sample."""
    return flag_exception_fn(
        sample_id, sample_identifier, finding_detail, citations
    ).model_dump()


@tool
def flag_pass(sample_id: str, sample_identifier: str, citations: list[str]) -> dict:
    """Flags a pass for a given sample."""
    return flag_pass_fn(sample_id, sample_identifier, citations).model_dump()


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
    llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)

    SYS_PROMPT = """You are a SOX ITGC Testing Agent.
You will be provided with a ControlDefinition and an EvidencePackage describing the files you have available.
You must execute the testing procedure described in the control strictly using the available tools.

Steps you normally take:
1. Load the evidence files using `load_evidence`.
2. Perform necessary data joins if needed using `join_datasets`.
3. Iterate through each sample based on the Control threshold rules.
   - You may use `calculate_delta` or `lookup_record`.
   - IMPORTANT: `lookup_record` might return a 'not_found' dictionary if the record does not exist. This is a critical finding if the rule requires the record to exist (for example, account disable event). Do not assume missing records are errors in your logic; they are control exceptions.
4. Call `flag_exception` or `flag_pass` for EVERY sample evaluated based on the rules. Each time you call these tools, the system will remember the resulting finding for workpaper generation.
5. ONLY AFTER you have collected all the results from the `flag_exception` and `flag_pass` tool calls in previous turns, call `generate_workpaper` with the summarized counts and your overall conclusion.

CRITICAL RULES FOR `generate_workpaper`:
- DO NOT call `generate_workpaper` in the same response as `flag_pass` or `flag_exception`. Wait for those tool responses first.
- Call `generate_workpaper` EXACTLY ONCE for the entire test. Never call it in a loop or multiple times.
- When you call `generate_workpaper`, you MUST provide all of the following named arguments:
  - `total_samples`: the total number of samples you actually tested (integer).
  - `exceptions`: the total number of exceptions you identified (integer).
  - `conclusion`: a short narrative conclusion string.
- The control metadata and detailed findings will be pulled automatically from the prior `flag_pass` and `flag_exception` tool calls.
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
