import json
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.tencent_cos_utils import cos_client


class ProjectAssetTypeEnum(str, Enum):
    character = "character"
    location = "location"
    prop = "prop"


# ============ Response Schemas ============

class ProjectCharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str
    name: str
    aliases: Optional[str] = None
    description: Optional[str] = None
    profile_data: Optional[str] = None
    image_url: Optional[str] = None
    previous_image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    image_model_system_prompt: Optional[str] = None
    gen_status: str = "pending"
    voice_id: Optional[str] = None
    voice_type: Optional[str] = None
    custom_voice_url: Optional[str] = None
    volc_private_asset_id: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    source_global_id: Optional[str] = None

    @field_validator("image_url", "previous_image_url", mode="before")
    @classmethod
    def _resolve_image_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v

    @field_validator("thumbnail_url", mode="before")
    @classmethod
    def _resolve_thumbnail_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v

    @field_validator("custom_voice_url", mode="before")
    @classmethod
    def _resolve_voice_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v


class ProjectLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str
    name: str
    place: Optional[str] = None
    time: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    previous_image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    image_model_system_prompt: Optional[str] = None
    gen_status: str = "pending"
    volc_private_asset_id: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    source_global_id: Optional[str] = None

    @field_validator("image_url", "previous_image_url", mode="before")
    @classmethod
    def _resolve_image_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v

    @field_validator("thumbnail_url", mode="before")
    @classmethod
    def _resolve_thumbnail_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v


class ProjectPropResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_encoders={
        datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
    })

    id: str
    name: str
    aliases: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    previous_image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    image_model_system_prompt: Optional[str] = None
    gen_status: str = "pending"
    volc_private_asset_id: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    thumbnail_url: Optional[str] = None
    source_global_id: Optional[str] = None

    @field_validator("image_url", "previous_image_url", mode="before")
    @classmethod
    def _resolve_image_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v

    @field_validator("thumbnail_url", mode="before")
    @classmethod
    def _resolve_thumbnail_url(cls, v):
        if v and not v.startswith("http"):
            return cos_client.key_to_url(v)
        return v


# ============ Stats & List ============

class ProjectAssetStatsResponse(BaseModel):
    total: int = 0
    pending: int = 0
    generating: int = 0
    completed: int = 0
    failed: int = 0


class ProjectAssetListResponse(BaseModel):
    characters: list[ProjectCharacterResponse] = []
    locations: list[ProjectLocationResponse] = []
    props: list[ProjectPropResponse] = []
    all_ready: bool = False
    stats: ProjectAssetStatsResponse


# ============ Update Request Schemas ============

class ProjectCharacterUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    aliases: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = Field(None, max_length=2000)
    profile_data: Optional[str] = Field(None, max_length=2000)
    image_model_system_prompt: Optional[str] = Field(None, max_length=2000)
    voice_id: Optional[str] = Field(None, max_length=128)
    voice_type: Optional[str] = Field(None, max_length=64)
    custom_voice_url: Optional[str] = Field(None, max_length=1024)


class ProjectLocationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    place: Optional[str] = Field(None, max_length=1000)
    time: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    image_model_system_prompt: Optional[str] = Field(None, max_length=2000)


class ProjectPropUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    aliases: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = Field(None, max_length=2000)
    image_model_system_prompt: Optional[str] = Field(None, max_length=2000)


# ============ Create Request Schemas ============

class ProjectCharacterCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    aliases: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectLocationCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    place: Optional[str] = Field(None, max_length=1000)
    time: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = Field(None, max_length=2000)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectPropCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    aliases: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = Field(None, max_length=2000)


# ============ Parse Response ============

class ProjectAssetParseResponse(BaseModel):
    characters_count: int = 0
    locations_count: int = 0
    props_count: int = 0
    episodes_count: int = 0
    storyboards_count: int = 0


# ============ Action Request Schemas ============

class ProjectAssetModifyImageRequest(BaseModel):
    modify_prompt: str = Field(..., min_length=1, max_length=2000)
    extra_image_urls: Optional[list[str]] = Field(None, max_length=3)


class ProjectAssetReferenceGenerateRequest(BaseModel):
    reference_image_urls: list[str] = Field(..., min_length=1, max_length=5)
    description: Optional[str] = Field(None, max_length=2000)
    mode: str = Field("direct", pattern="^(direct|extract)$")


class ProjectAssetExtractDescriptionRequest(BaseModel):
    reference_image_urls: list[str] = Field(..., min_length=1, max_length=5)


class ProjectAssetAiModifyDescriptionRequest(BaseModel):
    modify_instruction: str = Field(..., min_length=1, max_length=1000)


# ============ Copy From Global ============

class CopyFromGlobalRequest(BaseModel):
    global_asset_id: str = Field(..., min_length=1, description="全局资产ID")
