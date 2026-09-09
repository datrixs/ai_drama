from langgraph.graph import StateGraph, END

from app.graphs.states import DesignLocationState
from app.graphs.nodes.common import (
    validate_task, report_progress, handle_error, finalize_result,
    human_review_gate,
)
from app.graphs.nodes.text import (
    build_location_design_prompt, call_llm,
    parse_location_json_result, validate_location_description,
)


def create_design_location_graph() -> StateGraph:
    graph = StateGraph(DesignLocationState)

    graph.add_node("validate_task", validate_task)
    graph.add_node("build_design_prompt", build_location_design_prompt)
    graph.add_node("call_llm", call_llm)
    graph.add_node("parse_json_result", parse_location_json_result)
    graph.add_node("validate_description", validate_location_description)
    graph.add_node("human_review_gate", human_review_gate)
    graph.add_node("report_progress", report_progress)
    graph.add_node("finalize_result", finalize_result)
    graph.add_node("handle_error", handle_error)

    graph.set_entry_point("validate_task")
    graph.add_edge("validate_task", "build_design_prompt")
    graph.add_edge("build_design_prompt", "report_progress")
    graph.add_edge("report_progress", "call_llm")
    graph.add_conditional_edges(
        "call_llm",
        _route_after_call,
        {
            "parse_json_result": "parse_json_result",
            "handle_error": "handle_error",
        },
    )
    graph.add_conditional_edges(
        "parse_json_result",
        _route_after_parse,
        {
            "validate_description": "validate_description",
            "handle_error": "handle_error",
        },
    )
    graph.add_conditional_edges(
        "validate_description",
        _route_after_validate,
        {
            "human_review_gate": "human_review_gate",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("human_review_gate", "finalize_result")
    graph.add_edge("finalize_result", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


def _route_after_call(state: DesignLocationState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "call_llm":
        return "handle_error"
    return "parse_json_result"


def _route_after_parse(state: DesignLocationState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "parse_json_result":
        return "handle_error"
    return "validate_description"


def _route_after_validate(state: DesignLocationState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "validate_description":
        return "handle_error"
    return "human_review_gate"
