"""
短视频生成相关模型
"""
from sqlalchemy import Column, BigInteger, Boolean, Integer, String, Text, JSON, DateTime

from app.models.base import BasicModel


class ShortVideoTask(BasicModel):
    """短视频生成任务"""
    __tablename__ = "short_video_task"

    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")

    generation_type = Column(
        String(20), nullable=False, default="reference",
        comment="生成类型: reference(参考模式)/first_last_frame(首尾帧模式)",
    )
    prompt_text = Column(Text, comment="用户输入的提示词")
    ratio = Column(String(10), default="16:9", comment="视频比例: 16:9/9:16/1:1 等")
    resolution = Column(String(10), default="720p", comment="分辨率: 480p/720p")
    duration = Column(Integer, default=5, comment="视频时长(秒)")
    generate_audio = Column(Boolean, default=True, comment="是否生成音频")

    region = Column(String(16), nullable=True, comment="任务提交时的用户区域: domestic-国内/overseas-国际")

    api_request_params = Column(JSON, comment="发送到API的完整请求参数")
    api_response_data = Column(JSON, comment="API返回的完整响应数据")
    api_task_id = Column(String(100), comment="火山方舟任务ID")

    video_url = Column(String(500), comment="生成的视频地址")
    thumbnail_url = Column(String(500), comment="缩略图地址")

    first_frame_url = Column(String(500), comment="首帧图片URL")
    first_frame_volc_id = Column(String(100), comment="首帧图片火山资产ID")
    first_frame_byteplus_id = Column(String(100), nullable=True, comment="首帧图片BytePlus资产ID")
    last_frame_url = Column(String(500), comment="尾帧图片URL")
    last_frame_volc_id = Column(String(100), comment="尾帧图片火山资产ID")
    last_frame_byteplus_id = Column(String(100), nullable=True, comment="尾帧图片BytePlus资产ID")

    reference_media_json = Column(Text, comment="参考媒体JSON: {imageUrls:[], videoUrls:[], audioUrls:[]}")

    status = Column(
        String(20), nullable=False, default="pending",
        comment="状态: pending/submitted/queued/processing/succeeded/failed/cancelled",
    )
    error_message = Column(Text, comment="错误信息")
    progress = Column(Integer, default=0, comment="进度百分比 0-100")

    submitted_at = Column(DateTime, comment="提交时间")
    started_at = Column(DateTime, comment="开始处理时间")
    completed_at = Column(DateTime, comment="完成时间")


class ShortVideoAsset(BasicModel):
    """短视频资产"""
    __tablename__ = "short_video_asset"

    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")
    project_id = Column(String(36), index=True, comment="关联项目ID(项目资产库时有值)")

    asset_name = Column(String(200), comment="资源名称(原始上传文件名)")
    asset_type = Column(String(20), nullable=False, comment="资源类型: image/video/audio")
    asset_url = Column(String(500), comment="资源地址(COS URL)")
    asset_size = Column(BigInteger, comment="文件大小(字节)")
    mime_type = Column(String(100), comment="MIME类型")

    volc_asset_id = Column(String(100), comment="火山引擎资产ID(同步后获得)")
    byteplus_asset_id = Column(String(100), nullable=True, comment="BytePlus 资产ID(国际版同步后获得)")
    thumbnail_url = Column(String(500), comment="缩略图(视频/音频的封面图)")
    duration = Column(Integer, comment="视频/音频时长(秒)")

    source = Column(
        String(20), default="upload",
        comment="来源: upload(本地上传)/project_asset(项目资产)/asset_center(资产中心)",
    )
    source_asset_id = Column(String(36), comment="来源资产ID")
    metadata_json = Column(Text, comment="扩展元数据JSON")
