"""无限画布相关模型"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, JSON

from app.enums.canvas import CanvasItemType, CanvasItemRunStatus, CanvasGenerationStatus
from app.models.base import BasicModel


class CanvasDocument(BasicModel):
    """无限画布 - 画布"""
    __tablename__ = "canvas_document"

    user_id = Column(String(36), nullable=False, index=True, comment="所有者用户ID")
    title = Column(String(128), nullable=False, default="未命名画布", comment="画布标题")
    description = Column(Text, comment="画布描述")
    thumbnail_url = Column(String(500), comment="画布缩略图URL")
    last_opened_at = Column(DateTime, comment="最近一次打开时间")


class CanvasItem(BasicModel):
    """无限画布 - 节点"""
    __tablename__ = "canvas_item"

    canvas_id = Column(String(36), nullable=False, index=True, comment="所属画布ID")
    item_type = Column(
        String(16), nullable=False,
        default=CanvasItemType.TEXT,
        comment="节点类型: text/image/video/audio/group",
    )
    parent_id = Column(
        String(36), nullable=True, index=True,
        comment="所属组合节点ID（仅单层：指向 item_type=group 的节点；为空表示顶层节点）",
    )
    title = Column(String(128), default="", comment="节点标题")
    position_x = Column(Integer, default=0, comment="X 坐标")
    position_y = Column(Integer, default=0, comment="Y 坐标")
    width = Column(Integer, default=240, comment="节点宽度")
    height = Column(Integer, default=120, comment="节点高度")
    z_index = Column(Integer, default=0, comment="层级")
    content_json = Column(JSON, comment="节点内容：{prompt, ...}")
    generation_config_json = Column(JSON, comment="生成参数：{model, resolution, ratio, count, ...}")
    last_output_json = Column(JSON, comment="最近一次生成的输出")
    cover_url = Column(Text, comment="节点封面图URL（COS永久URL；图片=压缩缩略图，视频=ffmpeg首帧）")
    last_run_status = Column(
        String(16), nullable=False,
        default=CanvasItemRunStatus.IDLE,
        comment="最近一次生成状态: idle/pending/processing/completed/failed",
    )
    last_run_error = Column(Text, comment="最近一次生成的错误信息")
    # 资产库（火山引擎 / BytePlus）双字段：按用户区域同步对应一侧
    volc_asset_id = Column(String(128), index=True, comment="火山引擎私域资产ID（国内）")
    byteplus_asset_id = Column(String(128), index=True, comment="BytePlus 私域资产ID（国际）")
    asset_tag = Column(String(16), nullable=True, comment="资产标记: character/location/prop")
    saved_to_asset_center = Column(
        Boolean, nullable=False, default=False, server_default="0",
        comment="是否已保存到资产中心（保存到资产中心接口置 True，避免重复入库）",
    )
    voice_url = Column(Text, comment="角色音色音频 URL（character 节点用）")
    voice_cos_key = Column(String(512), comment="角色音色 COS key")

    @property
    def image_url(self):
        """供 sync_user_asset_to_volc 反射读取（永久 URL 优先）"""
        out = self.last_output_json or {}
        return out.get("url") or out.get("image_url")

    @property
    def asset_type(self):
        """供 sync_user_asset_to_volc 反射读取（按节点类型映射）

        sync_user_asset_to_volc 内部按 {image:Image, video:Video, audio:Audio} 推断
        火山 AssetType，因此 audio 节点必须返回 "audio"，否则会被误判为 image。
        """
        return {"image": "image", "video": "video", "audio": "audio", "text": "image"}.get(
            (self.item_type or "").lower(), "image"
        )


class CanvasConnection(BasicModel):
    """无限画布 - 节点之间的连线（有方向的引用）"""
    __tablename__ = "canvas_connection"

    canvas_id = Column(String(36), nullable=False, index=True, comment="所属画布ID")
    source_item_id = Column(String(36), nullable=False, index=True, comment="上游节点ID")
    target_item_id = Column(String(36), nullable=False, index=True, comment="下游节点ID")
    source_handle = Column(String(32), default="right", comment="上游节点连接点")
    target_handle = Column(String(32), default="left", comment="下游节点连接点")


class CanvasItemGeneration(BasicModel):
    """无限画布 - 节点生成历史"""
    __tablename__ = "canvas_item_generation"

    item_id = Column(String(36), nullable=False, index=True, comment="所属节点ID")
    document_id = Column(String(36), nullable=False, index=True, comment="所属画布ID（冗余，便于查询）")
    user_id = Column(String(36), nullable=False, index=True, comment="发起用户ID（冗余）")
    generation_type = Column(String(16), nullable=False, comment="生成类型: text/image/video/audio")
    input_json = Column(JSON, comment="本次生成的输入快照")
    output_json = Column(JSON, comment="本次生成的输出")
    ark_task_id = Column(String(64), index=True, comment="Seedance 任务 ID（冗余，回调匹配用）")
    model_call_log_id = Column(String(36), index=True, comment="关联的模型调用日志ID（model_call_log.id）")
    status = Column(
        String(16), nullable=False,
        default=CanvasGenerationStatus.IDLE,
        comment="状态: idle/pending/processing/completed/failed/canceled",
    )
    error_msg = Column(Text, comment="错误信息")
    started_at = Column(DateTime, comment="开始处理时间")
    finished_at = Column(DateTime, comment="完成时间")
