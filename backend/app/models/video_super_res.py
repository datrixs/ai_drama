"""
视频超分(画质增强)任务模型
"""
from sqlalchemy import Column, Boolean, Integer, String, Text, JSON, DateTime

from app.models.base import BasicModel


class VideoSuperResTask(BasicModel):
    """视频超分任务"""
    __tablename__ = "video_super_res_task"

    user_id = Column(String(36), nullable=False, index=True, comment="用户ID")

    # is_local_upload=True: 源视频是用户本地上传到 COS 的资源(source_video_url 为 COS 永久地址)
    # is_local_upload=False: 源视频是用户输入的在线 URL(source_video_url 原样保存,非 COS 资源)
    is_local_upload = Column(Boolean, nullable=False, default=True, comment="是否本地上传(True=COS资源,False=在线URL)")

    source_video_url = Column(String(500), nullable=False, comment="源视频URL(COS永久地址或在线URL,取决于is_local_upload)")
    source_thumbnail_url = Column(String(500), comment="源视频缩略图URL(COS永久)")
    source_video_name = Column(String(200), comment="源视频文件名")
    source_video_duration = Column(Integer, comment="源视频时长(秒)")

    # 超分参数整体存为 JSON,字段集与前端/火山 API 完全对齐:
    #   tool_version / scene / resolution / resolution_limit /
    #   bitrate_level / fps / callback_args / queue_id
    params = Column(JSON, comment="超分参数JSON(透传火山,字段集与火山API对齐)")

    # API 调用信息(审计/重试)
    # request_payload: 前端创建任务时下发的完整请求体(原始)
    # api_request_params: 后端提交火山时构造的完整请求体
    # api_submit_response: 火山 submit_task 同步返回的完整响应(含 task_id)
    # api_response_data: 火山回调时下发的完整数据
    # api_task_id: 火山返回的任务ID(submit_response 中提取)
    request_payload = Column(JSON, comment="前端创建任务时下发的完整请求体")
    api_request_params = Column(JSON, comment="提交到火山API的完整请求参数")
    api_submit_response = Column(JSON, comment="火山submit_task同步返回的完整响应")
    api_response_data = Column(JSON, comment="火山回调时下发的完整数据")
    api_task_id = Column(String(100), comment="火山返回的任务ID")

    # 结果视频
    result_video_url = Column(String(500), comment="超分结果视频URL(COS永久)")
    result_thumbnail_url = Column(String(500), comment="超分结果视频缩略图URL(COS永久)")
    result_storage_key = Column(String(512), comment="超分结果视频COS存储key")

    # 状态机
    status = Column(
        String(20), nullable=False, default="pending",
        comment="状态: pending/submitted/processing/succeeded/failed/cancelled",
    )
    error_message = Column(Text, comment="错误信息")
    progress = Column(Integer, default=0, comment="进度百分比 0-100")

    # 时间节点
    submitted_at = Column(DateTime, comment="提交到火山API的时间")
    started_at = Column(DateTime, comment="开始处理时间")
    completed_at = Column(DateTime, comment="完成时间")
