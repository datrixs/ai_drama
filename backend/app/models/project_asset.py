"""
项目资产库
"""
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship

from app.models.base import BasicModel


class ProjectCharacter(BasicModel):
    """项目人物（角色）"""
    __tablename__ = "project_character"

    project_id = Column(String(36), ForeignKey("project.id"), nullable=False, index=True, comment="项目ID")
    name = Column(String(256), nullable=False, comment="角色名")
    aliases = Column(Text, comment="别名/曾用名")
    description = Column(Text, comment="AI 生成的人物描述（可由用户修改）")
    profile_data = Column(Text, comment="角色设定（分号分隔的属性描述串，由 LLM 生成）")
    profile_confirmed = Column(Boolean, nullable=False, default=False, comment="角色设定是否已确认")

    voice_id = Column(String(128), comment="绑定的音色 ID")
    voice_type = Column(String(64), comment="音色类型")
    custom_voice_url = Column(String(1024), comment="自定义音色文件 URL")

    image_url = Column(String(1024), comment="当前图片 URL")
    previous_image_url = Column(String(1024), comment="上一张图片 URL（用于撤销）")
    thumbnail_url = Column(String(1024), comment="缩略图 COS key")
    previous_thumbnail_url = Column(String(1024), comment="上一张缩略图 COS key（用于撤销）")
    image_prompt = Column(Text, comment="图片生成提示词（可由用户修改后重新生成）")
    image_model_system_prompt = Column(Text, nullable=True, comment="图片生成时的系统级提示词")
    gen_status = Column(String(32), nullable=False, default="pending", comment="生成状态: pending/generating/completed/failed")

    source_global_id = Column(String(36), comment="从全局角色复制来源")
    volc_private_asset_id = Column(String(256), comment="火山私域素材ID")
    byteplus_asset_id = Column(String(256), nullable=True, comment="BytePlus 资产ID(国际版同步后获得)")

    volc_asset_url = Column(String(512), comment="SD2认证后的asset://URL")
    volc_asset_status = Column(String(32), default="pending", comment="pending/active/stale")
    volc_asset_reason = Column(String(256), comment="失效原因")

    project = relationship("Project", backref="characters")


class ProjectLocation(BasicModel):
    """项目场景"""
    __tablename__ = "project_location"

    project_id = Column(String(36), ForeignKey("project.id"), nullable=False, index=True, comment="项目ID")
    name = Column(String(256), nullable=False, comment="场景名")
    place = Column(Text, comment="场景地点")
    time = Column(Text, comment="场景时间")
    summary = Column(Text, comment="场景摘要（来自分析结果）")
    description = Column(Text, comment="场景图片描述（可由用户修改）")

    image_url = Column(String(1024), comment="当前图片 URL")
    previous_image_url = Column(String(1024), comment="上一张图片 URL（用于撤销）")
    thumbnail_url = Column(String(1024), comment="缩略图 COS key")
    previous_thumbnail_url = Column(String(1024), comment="上一张缩略图 COS key（用于撤销）")
    image_prompt = Column(Text, comment="图片生成提示词（可由用户修改后重新生成）")
    image_model_system_prompt = Column(Text, nullable=True, comment="图片生成时的系统级提示词")
    gen_status = Column(String(32), nullable=False, default="pending", comment="生成状态: pending/generating/completed/failed")

    source_global_id = Column(String(36), comment="从全局场景复制来源")
    volc_private_asset_id = Column(String(256), comment="火山私域素材ID")
    byteplus_asset_id = Column(String(256), nullable=True, comment="BytePlus 资产ID(国际版同步后获得)")

    project = relationship("Project", backref="locations")


class ProjectProp(BasicModel):
    """项目道具"""
    __tablename__ = "project_prop"

    project_id = Column(String(36), ForeignKey("project.id"), nullable=False, index=True, comment="项目ID")
    name = Column(String(256), nullable=False, comment="道具名")
    aliases = Column(Text, comment="别名/英文名")
    description = Column(Text, comment="AI 生成的道具描述（可由用户修改）")

    image_url = Column(String(1024), comment="当前图片 URL")
    previous_image_url = Column(String(1024), comment="上一张图片 URL（用于撤销）")
    thumbnail_url = Column(String(1024), comment="缩略图 COS key")
    previous_thumbnail_url = Column(String(1024), comment="上一张缩略图 COS key（用于撤销）")
    image_prompt = Column(Text, comment="图片生成提示词（可由用户修改后重新生成）")
    image_model_system_prompt = Column(Text, nullable=True, comment="图片生成时的系统级提示词")
    gen_status = Column(String(32), nullable=False, default="pending", comment="生成状态: pending/generating/completed/failed")

    source_global_id = Column(String(36), comment="从全局道具复制来源")
    volc_private_asset_id = Column(String(256), comment="火山私域素材ID")
    byteplus_asset_id = Column(String(256), nullable=True, comment="BytePlus 资产ID(国际版同步后获得)")

    project = relationship("Project", backref="props")


class Episode(BasicModel):
    """项目剧集"""
    __tablename__ = "episode"

    project_id = Column(String(36), nullable=False, index=True, comment="项目ID")
    episode_number = Column(Integer, nullable=False, comment="集号")
    title = Column(String(256), comment="本集标题")
    outline = Column(Text, comment="本集大纲")
    episode_script = Column(Text, comment="本集剧本")
    episode_script_status = Column(String(32), nullable=True, default="pending", comment="剧本生成状态: pending/generating/completed/failed")
    status = Column(String(32), nullable=False, default="pending", comment="状态: pending/generating/completed/failed")

    # 多模态脚本（LLM 生成的原始 JSON，用于重新生成和调试）
    script_json = Column(JSON, comment="多模态脚本JSON")
    script_plain_text = Column(Text, comment="可编辑的脚本纯文本镜像")


class Storyboard(BasicModel):
    """项目分镜（按片段保存，一个片段一条记录）"""
    __tablename__ = "storyboard"

    episode_id = Column(String(36), nullable=False, index=True, comment="剧集ID")
    segment_index = Column(Integer, nullable=False, default=1, comment="片段序号（从1开始）")
    segment_intent = Column(Text, comment="片段意图描述")
    scene_summary = Column(Text, comment="场景总述")

    shots = Column(JSON, comment="镜头列表: [{index, durationHintSec, timeOfDay, sceneAssetId, characterAssetIds, camera, dialogue, action, soundEffect}]")

    # 视觉
    style_and_keywords = Column(Text, comment="风格和关键词")
    image_prompt = Column(Text, comment="片段图片生成提示词")
    image_url = Column(Text, comment="片段参考图URL（COS地址）")
    reference_images = Column(JSON, comment="参考图列表: [{url, assetId, label}]")

    # 视频
    video_prompt = Column(Text, comment="视频生成提示词")
    video_url = Column(Text, comment="最终视频URL（COS地址）")
    cover_url = Column(Text, comment="视频封面图URL（COS地址）")
    duration = Column(Float, comment="视频时长（秒）")
    resolution = Column(String(16), comment="分辨率: 480p/720p/1080p")

    # 首尾帧（用于连续片段视频生成传参）
    first_frame_url = Column(Text, comment="首帧图片URL")
    last_frame_url = Column(Text, comment="尾帧图片URL")

    # 视频生成任务
    ark_task_id = Column(String(256), comment="火山引擎视频生成任务ID")
    api_response_data = Column(JSON, comment="方舟回调原始数据（用于异步上传 COS 前的源地址 fallback）")

    # 状态
    status = Column(String(32), default="pending", comment="状态: pending/image_generating/image_completed/video_generating/video_completed/failed")
    gen_error = Column(Text, comment="生成错误信息")

    # 原始数据
    raw_text = Column(Text, comment="LLM生成的原始文本")


class EpisodeConcatRecord(BasicModel):
    """剧集整集视频合成记录"""
    __tablename__ = "episode_concat_record"

    user_id = Column(String(36), nullable=False, index=True, comment="操作用户ID")
    episode_id = Column(String(36), nullable=False, index=True, comment="剧集ID")
    project_id = Column(String(36), nullable=False, index=True, comment="项目ID")

    # 合成时使用的源视频 URL 列表（按 segment_index 排序）：[{segment_index, video_url}]
    source_video_urls = Column(JSON, comment="合成时使用的源视频URL列表")
    segment_count = Column(Integer, nullable=False, default=0, comment="源视频片段数量")

    # 合成产物
    result_video_url = Column(String(1024), nullable=True, comment="合成产物URL（COS永久）")
    result_storage_key = Column(String(512), nullable=True, comment="合成产物COS key")
    duration_sec = Column(Float, nullable=True, comment="合成视频时长（秒）")

    # 状态
    status = Column(String(32), nullable=False, default="pending",
                    comment="状态: pending/processing/completed/failed")
    error_message = Column(Text, nullable=True, comment="失败原因")
