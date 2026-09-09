from langgraph.graph import StateGraph, END

from app.graphs.states import GenerateImageState
from app.graphs.nodes.common import (
    validate_task, report_progress, handle_error, finalize_result,
    human_review_gate,
)
from app.graphs.nodes.image import (
    load_appearance_generate, build_image_prompt, generate_images,
    update_appearance_db,
)


def create_generate_image_graph() -> StateGraph:
    graph = StateGraph(GenerateImageState)

    graph.add_node("validate_task", validate_task)
    graph.add_node("load_appearance", load_appearance_generate)
    graph.add_node("build_image_prompt", build_image_prompt)
    graph.add_node("generate_images", generate_images)
    graph.add_node("update_appearance_db", update_appearance_db)
    graph.add_node("human_review_gate", human_review_gate)
    graph.add_node("report_progress", report_progress)
    graph.add_node("finalize_result", finalize_result)
    graph.add_node("handle_error", handle_error)

    graph.set_entry_point("validate_task")
    graph.add_edge("validate_task", "load_appearance")
    graph.add_conditional_edges(
        "load_appearance",
        _route_after_load,
        {
            "build_image_prompt": "build_image_prompt",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("build_image_prompt", "report_progress")
    graph.add_edge("report_progress", "generate_images")
    graph.add_conditional_edges(
        "generate_images",
        _route_after_generate,
        {
            "update_appearance_db": "update_appearance_db",
            "handle_error": "handle_error",
        },
    )
    graph.add_conditional_edges(
        "update_appearance_db",
        _route_after_update,
        {"human_review_gate": "human_review_gate", "handle_error": "handle_error"},
    )
    graph.add_edge("human_review_gate", "finalize_result")
    graph.add_edge("finalize_result", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


def _route_after_load(state: GenerateImageState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "load_appearance_generate":
        return "handle_error"
    return "build_image_prompt"


def _route_after_generate(state: GenerateImageState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "generate_images":
        return "handle_error"
    return "update_appearance_db"


def _route_after_update(state: GenerateImageState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "update_appearance_db":
        return "handle_error"
    return "human_review_gate"
