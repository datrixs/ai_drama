from langgraph.graph import StateGraph, END

from app.graphs.states import ReferenceToCharacterState
from app.graphs.nodes.common import (
    validate_task, report_progress, handle_error, finalize_result,
    human_review_gate,
)
from app.graphs.nodes.vision import (
    load_reference_config, route_by_extract_only,
    call_vision, extract_description,
    build_image_prompt, generate_ref_images,
    optional_extract_description, update_appearance_db,
)


def create_reference_to_character_graph() -> StateGraph:
    graph = StateGraph(ReferenceToCharacterState)

    graph.add_node("validate_task", validate_task)
    graph.add_node("load_reference_config", load_reference_config)
    graph.add_node("call_vision", call_vision)
    graph.add_node("extract_description", extract_description)
    graph.add_node("build_image_prompt", build_image_prompt)
    graph.add_node("generate_ref_images", generate_ref_images)
    graph.add_node("optional_extract_description", optional_extract_description)
    graph.add_node("update_appearance_db", update_appearance_db)
    graph.add_node("human_review_gate", human_review_gate)
    graph.add_node("report_progress", report_progress)
    graph.add_node("finalize_result", finalize_result)
    graph.add_node("handle_error", handle_error)

    graph.set_entry_point("validate_task")
    graph.add_edge("validate_task", "load_reference_config")

    # 条件分支：extract_only 走视觉提取，否则走图生图
    graph.add_conditional_edges(
        "load_reference_config",
        route_by_extract_only,
        {
            "call_vision": "call_vision",
            "build_image_prompt": "build_image_prompt",
        },
    )

    # extract_only 分支
    graph.add_conditional_edges(
        "call_vision",
        _route_after_vision,
        {
            "extract_description": "extract_description",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("extract_description", "human_review_gate")

    # 图生图分支
    graph.add_edge("build_image_prompt", "report_progress")
    graph.add_edge("report_progress", "generate_ref_images")
    graph.add_conditional_edges(
        "generate_ref_images",
        _route_after_generate,
        {
            "optional_extract_description": "optional_extract_description",
            "handle_error": "handle_error",
        },
    )
    graph.add_edge("optional_extract_description", "update_appearance_db")
    graph.add_edge("update_appearance_db", "human_review_gate")

    # 汇合
    graph.add_edge("human_review_gate", "finalize_result")
    graph.add_edge("finalize_result", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


def _route_after_vision(state: ReferenceToCharacterState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "call_vision":
        return "handle_error"
    return "extract_description"


def _route_after_generate(state: ReferenceToCharacterState) -> str:
    errors = state.get("errors", [])
    if errors and errors[-1].get("node") == "generate_ref_images":
        return "handle_error"
    return "optional_extract_description"
