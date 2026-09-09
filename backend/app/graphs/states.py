from typing import TypedDict


class BaseWorkflowState(TypedDict, total=False):
    task_id: str
    task_type: str
    payload: dict
    user_id: str
    progress: int
    status: str
    errors: list[dict]
    retry_count: int
    result_data: dict
    needs_human_review: bool


class DesignCharacterState(BaseWorkflowState, total=False):
    user_instruction: str
    prompt_text: str
    raw_completion: dict | None
    parsed_result: dict | None
    description: str


class ModifyCharacterState(BaseWorkflowState, total=False):
    current_description: str
    modify_instruction: str
    prompt_text: str
    raw_completion: dict | None
    parsed_result: dict | None
    description: str


class ReferenceToCharacterState(BaseWorkflowState, total=False):
    reference_image_urls: list[str]
    extract_only: bool
    art_style: str
    custom_description: str
    count: int
    prompt_text: str
    raw_completion: dict | None
    description: str
    image_results: list[dict]
    appearance_id: str | None
    is_background_job: bool


class GenerateImageState(BaseWorkflowState, total=False):
    asset_type: str
    asset_id: str
    appearance_index: int
    image_index: int
    count: int
    art_style: str
    descriptions: list[str]
    image_results: list[dict]
    image_keys: list[str]
    thumb_keys: list[str | None]


class ModifyImageState(BaseWorkflowState, total=False):
    asset_id: str
    asset_type: str
    asset_name: str
    appearance_index: int
    image_index: int
    modify_prompt: str
    reference_images: list[str]
    current_image_key: str | None
    new_image_key: str | None
    new_thumb_key: str | None
    new_description: str
    new_available_slots: str


class DesignLocationState(BaseWorkflowState, total=False):
    user_instruction: str
    prompt_text: str
    raw_completion: dict | None
    parsed_result: dict | None
    description: str
    available_slots: list[str]


class ModifyLocationState(BaseWorkflowState, total=False):
    location_name: str
    current_description: str
    modify_instruction: str
    prompt_text: str
    raw_completion: dict | None
    parsed_result: dict | None
    description: str
    available_slots: list[str]


class ModifyPropState(BaseWorkflowState, total=False):
    prop_name: str
    current_description: str
    modify_instruction: str
    prompt_text: str
    raw_completion: dict | None
    parsed_result: dict | None
    description: str


class VoiceDesignState(BaseWorkflowState, total=False):
    voice_prompt: str
    preview_text: str
    scheme_count: int
    language: str
    voice_schemes: list[dict]
    generated_count: int
