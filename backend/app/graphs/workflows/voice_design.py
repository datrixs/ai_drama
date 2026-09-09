from langgraph.graph import StateGraph, END

from app.graphs.states import VoiceDesignState
from app.graphs.nodes.common import (
    validate_task, report_progress, handle_error, finalize_result,
)
from app.graphs.nodes.audio import (
    validate_voice_input, generate_voice_scheme, should_continue_generating,
)


def create_voice_design_graph() -> StateGraph:
    graph = StateGraph(VoiceDesignState)

    graph.add_node("validate_task", validate_task)
    graph.add_node("validate_voice_input", validate_voice_input)
    graph.add_node("report_progress", report_progress)
    graph.add_node("generate_voice_scheme", generate_voice_scheme)
    graph.add_node("finalize_result", finalize_result)
    graph.add_node("handle_error", handle_error)

    graph.set_entry_point("validate_task")
    graph.add_edge("validate_task", "validate_voice_input")
    graph.add_conditional_edges(
        "validate_voice_input",
        _route_after_validate,
        {
            "report_progress": "report_progress",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("report_progress", "generate_voice_scheme")
    graph.add_conditional_edges(
        "generate_voice_scheme",
        should_continue_generating,
        {
            "generate_voice_scheme": "generate_voice_scheme",
            "finalize_result": "finalize_result",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("finalize_result", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


def _route_after_validate(state: VoiceDesignState) -> str:
    errors = state.get("errors", [])
    if errors:
        return "handle_error"
    return "report_progress"
