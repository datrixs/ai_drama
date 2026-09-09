"""无限画布 Schema"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import SchemaBase

ASSET_TAG_VALUES = {"character", "location", "prop"}


# ===== Prompt Token（@ 引用结构化 prompt） =====

class PromptToken(BaseModel):
    """一段 prompt：纯文本 或 @ 引用某个节点"""
    type: str = Field(description="text / mention")
    value: Optional[str] = Field(default=None, description="type=text 时的纯文本片段")
    node_id: Optional[str] = Field(default=None, description="type=mention 时引用的节点 id")
    node_type: Optional[str] = Field(default=None, description="mention 节点类型快照：text/image/video/audio")
    node_title: Optional[str] = Field(default=None, description="mention 节点标题快照（展示用）")
    role: Optional[str] = Field(default=None, description="image mention 的角色：first_frame/last_frame/reference")


# ===== 资产导入（上传 / 资产中心） =====

class RegisterAssetRequest(BaseModel):
    """把外部二进制资产登记到画布节点（直接当作一次完成的生成记录）"""
    source: str = Field(default="upload", description="upload / asset_center")
    url: str = Field(description="资产 COS URL")
    thumbnail_url: Optional[str] = Field(default=None, description="缩略图 URL（可选）")
    cos_key: Optional[str] = Field(default=None, description="COS key（可选）")
    filename: Optional[str] = Field(default=None, description="文件名")
    size: Optional[int] = Field(default=None, description="文件大小（字节）")
    asset_id: Optional[str] = Field(default=None, description="资产中心资产 id（source=asset_center 时填）")
    duration: Optional[float] = Field(default=None, description="音视频时长（秒，audio 必填用于 ≤15s 校验）")
    asset_type: Optional[str] = Field(
        default=None,
        description="显式资产类型 image/video/audio（默认按节点 item_type 推断）",
    )


class SaveToAssetCenterRequest(BaseModel):
    """画布节点保存到资产中心（角色/场景/道具/音色）"""
    asset_kind: str = Field(
        description="保存类型：image 节点 → character/location/prop；audio 节点 → voice"
    )
    folder_id: Optional[str] = Field(default=None, description="资产组 id（与 new_folder_name 二选一，都为空则不分组）")
    new_folder_name: Optional[str] = Field(default=None, description="新建资产组名称（与 folder_id 二选一）")
    name: Optional[str] = Field(default=None, description="资产名称（默认取节点标题）")


class BatchSaveToAssetCenterRequest(BaseModel):
    """批量保存到资产中心：按节点自身 asset_tag / item_type 自动归类

    - image + asset_tag∈{character/location/prop} → 对应类型
    - audio → voice
    候选过滤由后端完成（saved_to_asset_center=False 且 last_output_json 有 url）。
    """
    folder_id: Optional[str] = Field(default=None, description="资产组 id（与 new_folder_name 二选一）")
    new_folder_name: Optional[str] = Field(default=None, description="新建资产组名称（与 folder_id 二选一）")


# ===== 节点生成请求 =====

class CanvasGenerateTextRequest(BaseModel):
    """文本节点生成请求"""
    prompt: Optional[str] = None
    # 保持 list[dict]：下游 canvas_prompt.build_prompt_for_llm / collect_image_refs_by_role
    # 用 isinstance(tok, dict) 守卫，Pydantic 对象会被静默丢弃
    prompt_tokens: Optional[List[dict]] = None
    prompt_plain_text: Optional[str] = None
    model: Optional[str] = None


class CanvasGenerateImageRequest(BaseModel):
    """图片节点生成请求"""
    prompt: Optional[str] = None
    prompt_tokens: Optional[List[dict]] = None
    prompt_plain_text: Optional[str] = None
    model: Optional[str] = None
    ratio: Optional[str] = Field(default=None, description="3:2 / 1:1 / 2:3")
    model_key: Optional[str] = Field(default=None, description="默认 character_model")
    reference_image_urls: Optional[List[str]] = Field(default=None, description="参考图 URL（图生图），不传则只走文生图")
    image_style: Optional[str] = Field(default=None, description="图片风格 key：american-comic/chinese-comic/japanese-anime/realistic/custom；custom 表示不注入预设风格")


class CanvasGenerateVideoRequest(BaseModel):
    """视频节点生成请求"""
    prompt: Optional[str] = None
    prompt_tokens: Optional[List[dict]] = None
    prompt_plain_text: Optional[str] = None
    model: Optional[str] = None
    ratio: Optional[str] = Field(default=None, description="16:9 / 9:16 / 1:1")
    resolution: Optional[str] = Field(default=None, description="720p / 1080p")
    duration: Optional[int] = Field(default=None, description="秒")
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None
    reference_image_urls: Optional[List[str]] = None


# ===== 画布 =====

class CanvasDocumentCreate(BaseModel):
    """创建画布"""
    title: str = Field(default="未命名画布", max_length=128, description="画布标题")
    description: Optional[str] = Field(default=None, description="画布描述")


class CanvasDocumentUpdate(BaseModel):
    """更新画布"""
    title: Optional[str] = Field(default=None, max_length=128, description="画布标题")
    description: Optional[str] = Field(default=None, description="画布描述")
    thumbnail_url: Optional[str] = Field(default=None, description="画布缩略图URL")


class CanvasDocumentItem(SchemaBase):
    """画布列表项"""
    id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    last_opened_at: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ===== 节点 =====

class CanvasItemCreate(BaseModel):
    """创建节点"""
    item_type: str = Field(description="节点类型: text/image/video/audio/group")
    title: Optional[str] = Field(default="", max_length=128, description="节点标题")
    position_x: int = Field(default=0, description="X 坐标")
    position_y: int = Field(default=0, description="Y 坐标")
    width: int = Field(default=240, description="节点宽度")
    height: int = Field(default=120, description="节点高度")
    z_index: int = Field(default=0, description="层级")
    content_json: Optional[dict] = Field(default=None, description="节点内容")
    generation_config_json: Optional[dict] = Field(default=None, description="生成参数")
    parent_id: Optional[str] = Field(default=None, description="所属组合节点ID（仅单层，指向 group 节点）")
    asset_tag: Optional[str] = Field(default=None, description="资产标记: character/location/prop")
    voice_url: Optional[str] = Field(default=None, description="角色音色音频 URL")
    voice_cos_key: Optional[str] = Field(default=None, description="角色音色 COS key")

    @field_validator("asset_tag")
    @classmethod
    def _validate_asset_tag(cls, v):
        if v is None or v == "":
            return None
        if v not in ASSET_TAG_VALUES:
            raise ValueError("asset_tag must be one of character/location/prop or null")
        return v


class CanvasItemUpdate(BaseModel):
    """更新节点"""
    title: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    z_index: Optional[int] = None
    content_json: Optional[dict] = None
    generation_config_json: Optional[dict] = None
    last_output_json: Optional[dict] = None
    last_run_status: Optional[str] = None
    last_run_error: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, description="设为空字符串等价于解组（置空）")
    asset_tag: Optional[str] = Field(default=None, description="资产标记: character/location/prop；空串视作清除")
    voice_url: Optional[str] = Field(default=None, description="角色音色音频 URL；空串视作清除")
    voice_cos_key: Optional[str] = Field(default=None, description="角色音色 COS key")

    @field_validator("asset_tag")
    @classmethod
    def _validate_asset_tag(cls, v):
        if v is None or v == "":
            return None
        if v not in ASSET_TAG_VALUES:
            raise ValueError("asset_tag must be one of character/location/prop or null")
        return v


class CanvasItemItem(SchemaBase):
    """节点"""
    id: str
    canvas_id: str
    item_type: str
    title: Optional[str] = None
    position_x: int = 0
    position_y: int = 0
    width: int = 240
    height: int = 120
    z_index: int = 0
    content_json: Optional[dict] = None
    generation_config_json: Optional[dict] = None
    last_output_json: Optional[dict] = None
    last_run_status: str = "idle"
    last_run_error: Optional[str] = None
    cover_url: Optional[str] = None
    parent_id: Optional[str] = None
    asset_tag: Optional[str] = None
    saved_to_asset_center: bool = False
    voice_url: Optional[str] = None
    voice_cos_key: Optional[str] = None

    model_config = {"from_attributes": True}


class CanvasItemBatchUpdateEntry(BaseModel):
    """批量更新单条节点的最小字段（位置 + 父子关系）"""
    id: str = Field(description="节点ID")
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    parent_id: Optional[str] = Field(
        default=None,
        description="置空表示解组；指向 group 节点表示打组；未传（exclude_unset）表示不动",
    )


class CanvasItemBatchUpdate(BaseModel):
    """批量更新节点（打组/解组/组拖动一次性保存）"""
    updates: List[CanvasItemBatchUpdateEntry] = Field(default_factory=list)


# ===== 连线 =====

class CanvasConnectionCreate(BaseModel):
    """创建连线"""
    source_item_id: str = Field(description="上游节点ID")
    target_item_id: str = Field(description="下游节点ID")
    source_handle: Optional[str] = Field(default="right", description="上游连接点")
    target_handle: Optional[str] = Field(default="left", description="下游连接点")


class CanvasConnectionItem(SchemaBase):
    """连线"""
    id: str
    canvas_id: str
    source_item_id: str
    target_item_id: str
    source_handle: Optional[str] = None
    target_handle: Optional[str] = None

    model_config = {"from_attributes": True}


# ===== 画布详情（含所有节点和连线，一次性返回）=====

class CanvasDocumentDetail(CanvasDocumentItem):
    """画布详情"""
    items: List[CanvasItemItem] = []
    connections: List[CanvasConnectionItem] = []
