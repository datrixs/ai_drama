"""视频超分(画质增强)Schema

字段名与火山 AI MediaKit `POST /api/v1/tools/enhance-video` 文档对齐:
    video_url / tool_version / scene / resolution / resolution_limit /
    bitrate_level / fps / callback_args / queue_id

注意:
- Schema 接受**扁平**字段(前端按火山文档原样下发),后端内部打包到 `params` JSON 列存储
- 不做枚举校验,只做类型校验(枚举值由火山 API 校验)
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.base import SchemaBase
from app.utils.tencent_cos_utils import cos_client


# 火山超分参数键集合(用于 endpoint 把扁平字段打包到 params JSON)
SUPER_RES_PARAM_KEYS = (
    "tool_version",
    "scene",
    "resolution",
    "resolution_limit",
    "bitrate_level",
    "fps",
    "callback_args",
    "queue_id",
)


# ===== 视频超分任务 =====

class VideoSuperResTaskCreate(BaseModel):
    """创建视频超分任务请求

    源视频相关字段:
        source_video_url: 源视频 URL
            - is_local_upload=True(本地上传): COS 签名 URL,后端转永久 URL 存储
            - is_local_upload=False(在线 URL): 第三方直链,后端原样保存
        is_local_upload: 是否本地上传(默认 True)

    超分参数(扁平,与火山文档字段对齐,前端原样下发):
        tool_version: 工具版本 standard/professional
        scene: 画质场景 common/ugc/short_series/aigc/old_film (仅 standard 生效)
        resolution: 目标分辨率 240p/360p/480p/540p/720p/1080p/2k/4k
        resolution_limit: 短边像素限制 [128, 2160] (与 resolution 互斥)
        bitrate_level: 码率档位 low/medium/high
        fps: 帧率 [15, 120]
        callback_args: 自定义回调参数(≤512 字节)
        queue_id: 队列 ID
    """
    source_video_url: str = Field(description="源视频URL(本地上传时为COS签名URL,在线URL时为第三方直链)")

    # True=本地上传(COS 资源,后端转永久 URL);False=在线 URL(后端原样保存)
    is_local_upload: bool = Field(default=True, description="是否本地上传")

    # 源视频元信息(可选,前端上传时附带)
    source_thumbnail_url: Optional[str] = Field(default=None, description="源视频缩略图URL(可选)")
    source_video_name: Optional[str] = Field(default=None, description="源视频文件名(可选)")
    source_video_duration: Optional[int] = Field(default=None, description="源视频时长秒(可选)")

    # 火山超分参数(扁平,与文档对齐,前端原样下发)
    tool_version: Optional[str] = Field(default=None, description="工具版本: standard/professional")
    scene: Optional[str] = Field(
        default=None,
        description="画质场景(仅 tool_version=standard 生效): common/ugc/short_series/aigc/old_film",
    )
    resolution: Optional[str] = Field(
        default=None,
        description="目标分辨率: 240p/360p/480p/540p/720p/1080p/2k/4k (与 resolution_limit 互斥)",
    )
    resolution_limit: Optional[int] = Field(
        default=None,
        description="短边像素限制 [128, 2160] (与 resolution 互斥)",
    )
    bitrate_level: Optional[str] = Field(default=None, description="码率档位: low/medium/high")
    fps: Optional[float] = Field(default=None, description="帧率 [15, 120]")
    callback_args: Optional[str] = Field(default=None, description="自定义回调参数(≤512字节)")
    queue_id: Optional[str] = Field(default=None, description="队列 ID")

    def to_task_data(self) -> dict:
        """转换为 ORM 任务数据

        把扁平超分参数提取到 params(JSON 列),保持 DB schema 不变。
        """
        data = self.model_dump(exclude_none=True)
        params = {k: data.pop(k) for k in SUPER_RES_PARAM_KEYS if k in data}
        data["params"] = params
        return data


class VideoSuperResTaskItem(SchemaBase):
    """视频超分任务列表项

    `@model_validator(mode="after")` 自动对源视频相关 URL 做签名转换:
    - is_local_upload=True(本地上传): 源 URL 是 COS 资源,签名后返回
    - is_local_upload=False(在线 URL): 源 URL 是第三方地址,原样返回
    结果视频始终是 COS 资源,统一签名。
    """
    id: str
    is_local_upload: bool = True
    source_video_url: Optional[str] = None
    source_thumbnail_url: Optional[str] = None
    source_video_name: Optional[str] = None
    source_video_duration: Optional[int] = None
    result_video_url: Optional[str] = None
    result_thumbnail_url: Optional[str] = None
    status: str
    progress: int = 0
    error_message: Optional[str] = None
    params: Optional[dict] = None
    create_time: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _sign_urls_for_response(self) -> "VideoSuperResTaskItem":
        """响应时自动把永久 URL/key 转签名 URL;在线 URL 原样返回"""
        allow_external = not bool(self.is_local_upload)
        if self.source_video_url:
            self.source_video_url = cos_client.to_signed(self.source_video_url, allow_external=allow_external)
        if self.source_thumbnail_url:
            self.source_thumbnail_url = cos_client.to_signed(self.source_thumbnail_url, allow_external=allow_external)
        # 结果视频始终是 COS 资源(后端下载火山结果后上传 COS)
        if self.result_video_url:
            self.result_video_url = cos_client.to_signed(self.result_video_url)
        if self.result_thumbnail_url:
            self.result_thumbnail_url = cos_client.to_signed(self.result_thumbnail_url)
        return self


class VideoSuperResTaskDetail(VideoSuperResTaskItem):
    """视频超分任务详情"""
    api_request_params: Optional[dict] = None
    api_response_data: Optional[dict] = None
    api_task_id: Optional[str] = None
    result_storage_key: Optional[str] = None
