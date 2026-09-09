import json
from datetime import datetime
from typing import List, Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator


from app import schemas
from app.deps.base import PageParams
from app.utils.tencent_cos_utils import cos_client


class GlobalAssetFolderPageParams(PageParams):
    """文件夹列表查询参数"""
    name: Optional[str] = Field(Query(None, description="文件夹名称"))


class GlobalCharacterPageParams(PageParams):
    """角色列表查询参数"""
    folder_id: Optional[str] = Field(Query(None, description="文件夹ID"))
    name: Optional[str] = Field(Query(None, description="角色名称"))


class GlobalCharacterAppearancePageParams(PageParams):
    """角色形象列表查询参数"""
    character_id: Optional[str] = Field(Query(None, description="角色ID"))


class GlobalLocationPageParams(PageParams):
    """场景列表查询参数"""
    folder_id: Optional[str] = Field(Query(None, description="文件夹ID"))
    name: Optional[str] = Field(Query(None, description="场景名称"))
    asset_kind: Optional[str] = Field(Query(None, description="资产类型"))


class GlobalLocationImagePageParams(PageParams):
    """场景图片列表查询参数"""
    location_id: Optional[str] = Field(Query(None, description="场景ID"))


class GlobalVoicePageParams(PageParams):
    """音色列表查询参数"""
    folder_id: Optional[str] = Field(Query(None, description="文件夹ID"))
    name: Optional[str] = Field(Query(None, description="音色名称"))


# ============ GlobalAssetFolder ============

class GlobalAssetFolderCreate(BaseModel):
    """创建文件夹请求"""
    name: str = Field(..., min_length=1, max_length=256, description="文件夹名称")


class GlobalAssetFolderUpdate(BaseModel):
    """更新文件夹请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=256, description="文件夹名称")


class GlobalAssetFolderItem(BaseModel):
    """文件夹列表项"""
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str = Field(..., description="文件夹ID")
    name: str = Field(..., description="文件夹名称")
    user_id: str = Field(..., description="创建者ID")
    owner_user_id: Optional[str] = Field(None, description="主账号ID")
    is_shared: bool = Field(False, description="是否为共享文件夹")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")


class GlobalAssetFolderMsg(schemas.Msg):
    """单条文件夹响应"""
    data: Optional[GlobalAssetFolderItem] = Field(None, description="数据")


class GlobalAssetFolderPageMsg(schemas.PageMsg):
    """文件夹列表响应"""
    data: Optional[List[GlobalAssetFolderItem]] = Field(None, description="数据")



# ============ GlobalCharacterAppearance ============

class GlobalCharacterAppearanceCreate(BaseModel):
    """创建角色形象请求"""
    character_id: str = Field(..., description="角色ID")
    appearance_index: int = Field(0, description="形象序号（0=主形象）")
    change_reason: Optional[str] = Field("default", description="变更原因/标签")
    art_style: Optional[str] = Field(None, description="艺术风格")
    image_model_system_prompt: Optional[str] = Field(None, description="图生模型系统提示词")
    description: Optional[str] = Field(None, description="形象描述")
    descriptions: Optional[str] = Field(None, description="形象描述数组JSON")
    image_url: Optional[str] = Field(None, description="当前图片URL")
    image_media_id: Optional[str] = Field(None, description="图片媒体对象ID")
    image_urls: Optional[str] = Field(None, description="候选图片URL列表JSON")
    selected_index: Optional[int] = Field(None, description="当前选中的渲染图索引")


class GlobalCharacterAppearanceUpdate(BaseModel):
    """更新角色形象请求"""
    character_id: str = Field(..., description="角色ID")
    appearance_index: int = Field(..., description="形象序号")
    description_index: Optional[int] = Field(None, description="描述更新索引")
    change_reason: Optional[str] = Field(None, description="变更原因/标签")
    art_style: Optional[str] = Field(None, description="艺术风格")
    image_model_system_prompt: Optional[str] = Field(None, description="图生模型系统提示词")
    description: Optional[str] = Field(None, description="形象描述")
    descriptions: Optional[str] = Field(None, description="形象描述数组JSON")
    image_url: Optional[str] = Field(None, description="当前图片URL")
    image_media_id: Optional[str] = Field(None, description="图片媒体对象ID")
    image_urls: Optional[str] = Field(None, description="候选图片URL列表JSON")
    selected_index: Optional[int] = Field(None, description="当前选中的渲染图索引")
    previous_image_url: Optional[str] = Field(None, description="上一次图片URL")
    previous_image_media_id: Optional[str] = Field(None, description="上一次图片媒体对象ID")
    previous_image_urls: Optional[str] = Field(None, description="上一次图片URL列表JSON")
    previous_description: Optional[str] = Field(None, description="上一次描述词")
    previous_descriptions: Optional[str] = Field(None, description="上一次描述词数组JSON")
    volc_private_asset_id: Optional[str] = Field(None, description="火山私域素材ID")


class GlobalCharacterAppearanceItem(BaseModel):
    """角色形象列表项"""
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str = Field(..., description="形象ID")
    character_id: str = Field(..., description="角色ID")
    appearance_index: int = Field(..., description="形象序号")
    change_reason: Optional[str] = Field(None, description="变更原因/标签")
    art_style: Optional[str] = Field(None, description="艺术风格")
    image_model_system_prompt: Optional[str] = Field(None, description="图生模型系统提示词")
    description: Optional[str] = Field(None, description="形象描述")
    descriptions: Optional[str] = Field(None, description="形象描述数组JSON")
    image_url: Optional[str] = Field(None, description="当前图片URL")
    image_media_id: Optional[str] = Field(None, description="图片媒体对象ID")
    image_urls: Optional[str] = Field(None, description="候选图片URL列表JSON")
    selected_index: Optional[int] = Field(None, description="当前选中的渲染图索引")
    previous_image_url: Optional[str] = Field(None, description="上一次图片URL")
    previous_image_media_id: Optional[str] = Field(None, description="上一次图片媒体对象ID")
    previous_image_urls: Optional[str] = Field(None, description="上一次图片URL列表JSON")
    previous_description: Optional[str] = Field(None, description="上一次描述词")
    previous_descriptions: Optional[str] = Field(None, description="上一次描述词数组JSON")
    volc_private_asset_id: Optional[str] = Field(None, description="火山私域素材ID")
    gen_status: Optional[str] = Field("pending", description="生成状态: pending/generating/completed/failed")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    thumbnail_urls: Optional[str] = Field(None, description="候选缩略图URL列表JSON")

    @field_validator("image_url", "previous_image_url", "thumbnail_url", mode="before")
    @classmethod
    def _resolve_image_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v

    @field_validator("image_urls", "previous_image_urls", "thumbnail_urls", mode="before")
    @classmethod
    def _resolve_image_urls_json(cls, v):
        if not v:
            return v
        try:
            keys = json.loads(v) if isinstance(v, str) else v
            if isinstance(keys, list):
                resolved = [cos_client.key_to_url(k) if k and not k.startswith("http") else (k or "") for k in keys]
                return json.dumps(resolved)
        except (json.JSONDecodeError, TypeError):
            pass
        return v


class GlobalCharacterAppearanceMsg(schemas.Msg):
    """单条角色形象响应"""
    data: Optional[GlobalCharacterAppearanceItem] = Field(None, description="数据")


class GlobalCharacterAppearancePageMsg(schemas.PageMsg):
    """角色形象列表响应"""
    data: Optional[List[GlobalCharacterAppearanceItem]] = Field(None, description="数据")


# ============ GlobalCharacter ============

class GlobalCharacterCreate(BaseModel):
    """创建角色请求"""
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: str = Field(..., min_length=1, max_length=256, description="角色名称")
    aliases: Optional[str] = Field(None, description="角色别名")
    art_style: Optional[str] = Field(None, description="艺术风格")
    description: Optional[str] = Field(None, description="角色描述")
    profile_data: Optional[str] = Field(None, description="角色profile数据JSON")
    profile_confirmed: Optional[bool] = Field(False, description="角色信息是否已确认")
    voice_id: Optional[str] = Field(None, description="语音ID")
    voice_type: Optional[str] = Field(None, description="语音类型")
    custom_voice_url: Optional[str] = Field(None, description="自定义语音URL")
    custom_voice_media_id: Optional[str] = Field(None, description="自定义语音媒体对象ID")
    global_voice_id: Optional[str] = Field(None, description="绑定的全局音色ID")
    initial_image_url: Optional[str] = Field(None, description="初始图片URL")
    reference_image_urls: Optional[list[str]] = Field(None, description="参考图URL列表")
    generate_from_reference: Optional[bool] = Field(False, description="是否从参考图生成")
    custom_description: Optional[str] = Field(None, description="自定义描述（参考图模式）")
    count: Optional[int] = Field(None, description="图片生成数量")
    locale: Optional[str] = Field(None, description="语言环境")


class GlobalCharacterUpdate(BaseModel):
    """更新角色请求"""
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: Optional[str] = Field(None, min_length=1, max_length=256, description="角色名称")
    aliases: Optional[str] = Field(None, description="角色别名")
    profile_data: Optional[str] = Field(None, description="角色profile数据JSON")
    profile_confirmed: Optional[bool] = Field(None, description="角色信息是否已确认")
    voice_id: Optional[str] = Field(None, description="语音ID")
    voice_type: Optional[str] = Field(None, description="语音类型")
    custom_voice_url: Optional[str] = Field(None, description="自定义语音URL")
    custom_voice_media_id: Optional[str] = Field(None, description="自定义语音媒体对象ID")
    global_voice_id: Optional[str] = Field(None, description="绑定的全局音色ID")


class GlobalCharacterItem(BaseModel):
    """角色列表项"""
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str = Field(..., description="角色ID")
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: str = Field(..., description="角色名称")
    aliases: Optional[str] = Field(None, description="角色别名")
    profile_data: Optional[str] = Field(None, description="角色profile数据JSON")
    profile_confirmed: Optional[bool] = Field(False, description="角色信息是否已确认")
    voice_id: Optional[str] = Field(None, description="语音ID")
    voice_type: Optional[str] = Field(None, description="语音类型")
    custom_voice_url: Optional[str] = Field(None, description="自定义语音URL")
    custom_voice_media_id: Optional[str] = Field(None, description="自定义语音媒体对象ID")
    global_voice_id: Optional[str] = Field(None, description="绑定的全局音色ID")
    user_id: str = Field(..., description="创建者ID")
    owner_user_id: Optional[str] = Field(None, description="主账号ID")
    is_management_asset: bool = Field(False, description="是否为平台资产")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    appearances: Optional[List["GlobalCharacterAppearanceItem"]] = Field(None, description="形象列表")
    preview_url: Optional[str] = Field(None, description="预览图URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")

    @field_validator("custom_voice_url", mode="before")
    @classmethod
    def _resolve_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v


class GlobalCharacterMsg(schemas.Msg):
    """单条角色响应"""
    data: Optional[GlobalCharacterItem] = Field(None, description="数据")


class GlobalCharacterPageMsg(schemas.PageMsg):
    """角色列表响应"""
    data: Optional[List[GlobalCharacterItem]] = Field(None, description="数据")


class GlobalCharacterCreateResultItem(BaseModel):
    character: Optional[GlobalCharacterItem] = None
    appearance: Optional[GlobalCharacterAppearanceItem] = None


class GlobalCharacterCreateMsg(schemas.Msg):
    data: Optional[GlobalCharacterCreateResultItem] = None


class GlobalCharacterDetailItem(BaseModel):
    character: Optional[GlobalCharacterItem] = None
    appearances: Optional[List[GlobalCharacterAppearanceItem]] = None


class GlobalCharacterDetailMsg(schemas.Msg):
    data: Optional[GlobalCharacterDetailItem] = None



# ============ GlobalLocation ============

class GlobalLocationCreate(BaseModel):
    """创建场景请求"""
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: str = Field(..., min_length=1, max_length=256, description="场景/道具名称")
    art_style: Optional[str] = Field(None, description="艺术风格")
    summary: Optional[str] = Field(None, description="简要描述")
    description: Optional[str] = Field(None, description="详细描述（道具专用，seed 到 image 记录）")
    asset_kind: Optional[str] = Field("location", description="资产类型：location/prop")
    count: Optional[int] = Field(1, ge=1, le=6, description="生成图片数量")


class GlobalLocationUpdate(BaseModel):
    """更新场景请求"""
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: Optional[str] = Field(None, min_length=1, max_length=256, description="场景/道具名称")
    art_style: Optional[str] = Field(None, description="艺术风格")
    summary: Optional[str] = Field(None, description="简要描述")
    asset_kind: Optional[str] = Field(None, description="资产类型：location/prop")


class GlobalLocationItem(BaseModel):
    """场景列表项"""
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str = Field(..., description="场景ID")
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: str = Field(..., description="场景/道具名称")
    art_style: Optional[str] = Field(None, description="艺术风格")
    summary: Optional[str] = Field(None, description="简要描述")
    asset_kind: Optional[str] = Field("location", description="资产类型：location/prop")
    user_id: str = Field(..., description="创建者ID")
    owner_user_id: Optional[str] = Field(None, description="主账号ID")
    is_management_asset: bool = Field(False, description="是否为平台资产")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    images: Optional[List["GlobalLocationImageItem"]] = Field(None, description="图片列表")
    preview_url: Optional[str] = Field(None, description="预览图URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")


class GlobalLocationMsg(schemas.Msg):
    """单条场景响应"""
    data: Optional[GlobalLocationItem] = Field(None, description="数据")


class GlobalLocationPageMsg(schemas.PageMsg):
    """场景列表响应"""
    data: Optional[List[GlobalLocationItem]] = Field(None, description="数据")


# ============ GlobalLocationImage ============

class GlobalLocationImageCreate(BaseModel):
    """创建场景图片请求"""
    location_id: str = Field(..., description="场景ID")
    image_index: int = Field(0, description="图片序号")
    image_model_system_prompt: Optional[str] = Field(None, description="图生模型系统提示词")
    description: Optional[str] = Field(None, description="图片描述")
    available_slots: Optional[str] = Field(None, description="可用槽位信息")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_media_id: Optional[str] = Field(None, description="图片媒体对象ID")
    is_selected: Optional[bool] = Field(False, description="是否为选中图片")


class GlobalLocationImageUpdate(BaseModel):
    """更新场景图片请求"""
    image_model_system_prompt: Optional[str] = Field(None, description="图生模型系统提示词")
    description: Optional[str] = Field(None, description="图片描述")
    available_slots: Optional[str] = Field(None, description="可用槽位信息")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_media_id: Optional[str] = Field(None, description="图片媒体对象ID")
    is_selected: Optional[bool] = Field(None, description="是否为选中图片")
    previous_image_url: Optional[str] = Field(None, description="上一次图片URL")
    previous_image_media_id: Optional[str] = Field(None, description="上一次图片媒体对象ID")
    previous_description: Optional[str] = Field(None, description="上一次描述词")
    volc_private_asset_id: Optional[str] = Field(None, description="火山私域素材ID")


class GlobalLocationImageItem(BaseModel):
    """场景图片列表项"""
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str = Field(..., description="图片ID")
    location_id: str = Field(..., description="场景ID")
    image_index: int = Field(..., description="图片序号")
    image_model_system_prompt: Optional[str] = Field(None, description="图生模型系统提示词")
    description: Optional[str] = Field(None, description="图片描述")
    available_slots: Optional[str] = Field(None, description="可用槽位信息")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_media_id: Optional[str] = Field(None, description="图片媒体对象ID")
    is_selected: Optional[bool] = Field(False, description="是否为选中图片")
    previous_image_url: Optional[str] = Field(None, description="上一次图片URL")
    previous_image_media_id: Optional[str] = Field(None, description="上一次图片媒体对象ID")
    previous_description: Optional[str] = Field(None, description="上一次描述词")
    volc_private_asset_id: Optional[str] = Field(None, description="火山私域素材ID")
    gen_status: Optional[str] = Field("pending", description="生成状态: pending/generating/completed/failed")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")

    @field_validator("image_url", "previous_image_url", "thumbnail_url", mode="before")
    @classmethod
    def _resolve_image_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v


class GlobalLocationImageMsg(schemas.Msg):
    """单条场景图片响应"""
    data: Optional[GlobalLocationImageItem] = Field(None, description="数据")


class GlobalLocationImagePageMsg(schemas.PageMsg):
    """场景图片列表响应"""
    data: Optional[List[GlobalLocationImageItem]] = Field(None, description="数据")


# ============ GlobalVoice ============

class GlobalVoiceCreate(BaseModel):
    """创建音色请求"""
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: str = Field(..., min_length=1, max_length=256, description="音色名称")
    description: Optional[str] = Field(None, description="详细描述")
    voice_id: Optional[str] = Field(None, description="qwen-tts voice ID")
    voice_type: Optional[str] = Field("qwen-designed", description="音色类型")
    custom_voice_url: Optional[str] = Field(None, description="上传音频URL")
    custom_voice_media_id: Optional[str] = Field(None, description="上传音频媒体对象ID")
    voice_prompt: Optional[str] = Field(None, description="AI设计提示词")
    gender: Optional[str] = Field(None, max_length=32, description="性别")
    language: Optional[str] = Field("zh", max_length=32, description="语言")


class GlobalVoiceUpdate(BaseModel):
    """更新音色请求"""
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: Optional[str] = Field(None, min_length=1, max_length=256, description="音色名称")
    description: Optional[str] = Field(None, description="详细描述")
    voice_id: Optional[str] = Field(None, description="qwen-tts voice ID")
    voice_type: Optional[str] = Field(None, description="音色类型")
    custom_voice_url: Optional[str] = Field(None, description="上传音频URL")
    custom_voice_media_id: Optional[str] = Field(None, description="上传音频媒体对象ID")
    voice_prompt: Optional[str] = Field(None, description="AI设计提示词")
    gender: Optional[str] = Field(None, max_length=32, description="性别")
    language: Optional[str] = Field(None, max_length=32, description="语言")


class GlobalVoiceItem(BaseModel):
    """音色列表项"""
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str = Field(..., description="音色ID")
    folder_id: Optional[str] = Field(None, description="文件夹ID")
    name: str = Field(..., description="音色名称")
    description: Optional[str] = Field(None, description="详细描述")
    voice_id: Optional[str] = Field(None, description="qwen-tts voice ID")
    voice_type: Optional[str] = Field("qwen-designed", description="音色类型")
    custom_voice_url: Optional[str] = Field(None, description="上传音频URL")
    custom_voice_media_id: Optional[str] = Field(None, description="上传音频媒体对象ID")
    voice_prompt: Optional[str] = Field(None, description="AI设计提示词")
    gender: Optional[str] = Field(None, description="性别")
    language: Optional[str] = Field("zh", description="语言")
    volc_private_asset_id: Optional[str] = Field(None, description="火山私域素材ID")
    duration: Optional[int] = Field(None, description="音频时长(秒)")
    user_id: str = Field(..., description="创建者ID")
    owner_user_id: Optional[str] = Field(None, description="主账号ID")
    is_management_asset: bool = Field(False, description="是否为平台资产")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    @field_validator("custom_voice_url", mode="before")
    @classmethod
    def _resolve_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v


class GlobalVoiceMsg(schemas.Msg):
    """单条音色响应"""
    data: Optional[GlobalVoiceItem] = Field(None, description="数据")


class GlobalVoicePageMsg(schemas.PageMsg):
    """音色列表响应"""
    data: Optional[List[GlobalVoiceItem]] = Field(None, description="数据")


# ============ AI 任务相关 Schema ============

class SelectImageRequest(BaseModel):
    """选择候选图请求"""
    type: str = Field("character", description="资产类型")
    id: str = Field(..., description="资产ID")
    appearance_index: int = Field(0, description="外观序号")
    image_index: Optional[int] = Field(None, description="图片索引")
    confirm: bool = Field(False, description="是否确认选择")


class UndoImageRequest(BaseModel):
    """撤销图片请求"""
    type: str = Field("character", description="资产类型")
    id: str = Field(..., description="资产ID")
    appearance_index: int = Field(0, description="外观序号")


class VoiceSettingsUpdate(BaseModel):
    """语音设置更新"""
    character_id: str = Field(..., description="角色ID")
    voice_type: Optional[str] = Field(None, description="语音类型")
    voice_id: Optional[str] = Field(None, description="语音ID")
    custom_voice_url: Optional[str] = Field(None, description="自定义语音URL")


class UploadImageResultItem(BaseModel):
    image_key: Optional[str] = None
    image_index: Optional[int] = None


class UploadImageMsg(schemas.Msg):
    data: Optional[UploadImageResultItem] = None


class VoiceUploadResultItem(BaseModel):
    audio_url: Optional[str] = None


class VoiceUploadMsg(schemas.Msg):
    data: Optional[VoiceUploadResultItem] = None


# ============ AI 音色设计 Schema ============

class VoiceDesignRequest(BaseModel):
    voice_prompt: str = Field(..., min_length=1, max_length=500, description="音色描述文本")
    preview_text: str = Field(..., min_length=5, max_length=300, description="试听文本")
    count: int = Field(3, ge=1, le=5, description="生成方案数量")
    language: str = Field("zh", max_length=10, description="语言")


# ============ Picker 资产选择器 Schema ============

class PickerCharacterItem(BaseModel):
    id: str
    name: str
    folder_name: Optional[str] = Field(None, description="文件夹名称")
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    appearance_count: int = 0
    has_voice: bool = False


class PickerLocationItem(BaseModel):
    id: str
    name: str
    summary: Optional[str] = None
    folder_name: Optional[str] = Field(None, description="文件夹名称")
    preview_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_count: int = 0
    asset_kind: Optional[str] = Field(None, description="location/prop")


class PickerVoiceItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    folder_name: Optional[str] = Field(None, description="文件夹名称")
    preview_url: Optional[str] = None
    voice_id: Optional[str] = None
    voice_type: Optional[str] = None
    gender: Optional[str] = None
    language: Optional[str] = None


class PickerMsg(schemas.Msg):
    data: Optional[dict] = None


# ============ 直传凭证 Schema ============

class UploadCredentialRequest(BaseModel):
    """获取直传凭证请求"""
    category: str = Field(..., description="上传分类: upload")
    biz: str = Field(..., description="业务标识: char / loc / prop / temp / project-character 等")
    file_extension: str = Field("jpg", description="文件扩展名（不含点）")
    content_type: str = Field("image/jpeg", description="MIME 类型")


class UploadCredentialResult(BaseModel):
    """直传凭证响应"""
    upload_url: str = Field(..., description="预签名上传 URL")
    cos_key: str = Field(..., description="COS 存储路径")
    url: str = Field(..., description="签名访问 URL")
    expires_in: int = Field(..., description="有效期（秒）")


class UploadCredentialMsg(schemas.Msg):
    data: Optional[UploadCredentialResult] = None


# ============ Upload Temp 临时上传 Schema ============

class UploadTempRequest(BaseModel):
    cos_key: Optional[str] = Field(None, description="前端直传后的 COS key（新模式）")
    image_base64: Optional[str] = Field(None, description="Base64图片 data URI")
    base64: Optional[str] = Field(None, description="Base64数据")
    extension: Optional[str] = Field(None, description="文件扩展名")


class UploadTempResultItem(BaseModel):
    url: Optional[str] = None
    key: Optional[str] = None


class UploadTempMsg(schemas.Msg):
    data: Optional[UploadTempResultItem] = None


# ============ 生成图片 Schema ============

from enum import Enum


class AssetType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    PROP = "prop"


class GenerateImageRequest(BaseModel):
    type: AssetType = Field(AssetType.CHARACTER, description="资产类型")
    id: str = Field(..., min_length=1, description="资产ID")
    appearance_index: int = Field(0, ge=0, description="外观序号")
    image_index: int = Field(0, ge=0, description="图片索引")
    count: int = Field(3, ge=1, le=6, description="生成图片数量")
    art_style: str = Field("", description="艺术风格")


# ============ 前向引用重建 ============

GlobalCharacterItem.model_rebuild()
GlobalLocationItem.model_rebuild()