from langgraph.graph import StateGraph, END

from app.graphs.states import ModifyImageState
from app.graphs.nodes.common import (
    validate_task, report_progress, handle_error, finalize_result,
    human_review_gate,
)
from app.graphs.nodes.image import (
    load_appearance_modify, load_reference_image, generate_modified_image,
    update_modify_db, sync_description_after_modify,
)


def create_modify_image_graph() -> StateGraph:
    graph = StateGraph(ModifyImageState)

    graph.add_node("validate_task", validate_task)
    graph.add_node("load_appearance", load_appearance_modify)
    graph.add_node("load_reference_image", load_reference_image)
    graph.add_node("generate_images", generate_modified_image)
    graph.add_node("sync_description", sync_description_after_modify)
    graph.add_node("update_appearance_db", update_modify_db)
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
            "load_reference_image": "load_reference_image",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("load_reference_image", "report_progress")
    graph.add_edge("report_progress", "generate_images")
    graph.add_conditional_edges(
        "generate_images",
        _route_after_generate,
        {
            "sync_description": "sync_description",
            "update_appearance_db": "update_appearance_db",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("sync_description", "update_appearance_db")
    graph.add_edge("update_appearance_db", "human_review_gate")
    graph.add_edge("human_review_gate", "finalize_result")
    graph.add_edge("finalize_result", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


def _route_after_load(state: ModifyImageState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "load_appearance_modify":
        return "handle_error"
    return "load_reference_image"


def _route_after_generate(state: ModifyImageState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "generate_modified_image":
        return "handle_error"
    asset_type = state.get("asset_type", "character")
    if asset_type in ("location", "prop"):
        return "sync_description"
    return "update_appearance_db"
