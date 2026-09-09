"""
AI大模型Model
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean
from sqlalchemy.orm import relationship

from app.models import BasicModel
from app.enums import AIModelType, VideoResolutionType, SuperResResolutionType


class AIProvider(BasicModel):
    """模型供应商"""
    __tablename__ = "ai_provider"

    name = Column(String(128), comment="模型供应商名称")
    code = Column(String(128), unique=True, comment="模型供应商编号")
    base_url = Column(String(256), comment="大模型调用地址")
    description = Column(String(256), comment="描述")


class AIModel(BasicModel):
    """模型"""
    __tablename__ = "ai_model"

    provider_id = Column(String(256), comment="模型供应商ID")
    name = Column(String(256), comment="模型名称（对外展示）")
    model_name = Column(String(256), comment="模型名称（实际调用）")
    model_type = Column(String(256), comment=AIModelType.__doc__.strip())
    base_url = Column(String(256), comment="大模型调用地址，若为空使用AIProvider的base_url")

    # 计费方式（目前用于区分图片类模型计费）
    billing_type = Column(String(128), comment="计费方式，token: 按token计费，times：按次计费")

    # 供应商
    provider = relationship("AIProvider", foreign_keys=[provider_id], primaryjoin="AIModel.provider_id == AIProvider.id")


class AIModelPoint(BasicModel):
    """
    模型积分消耗表
    记录不同模型、不同参数下的积分消耗情况
    """
    __tablename__ = "ai_model_point"

    model_id = Column(String(256), comment="AIModel表ID")

    # 文本类模型计费
    input_point = Column(Numeric(precision=10, scale=2), comment="输入积分消耗（每百万token），文本类模型计费")
    output_point = Column(Numeric(precision=10, scale=2), comment="输出积分消耗（每百万token），文本类模型计费")

    # 图片类模型计费
    # 字节系积分使用（按张计算）
    is_character = Column(Boolean, comment="是否是生成角色图")
    image_point = Column(Numeric(precision=10, scale=2), comment="图片积分消耗（每张图片），图片类模型计费")
    # chatgpt系积分使用（按token计算）
    input_text_point = Column(Numeric(precision=10, scale=2), comment="生成图片输入文字消耗的积分")
    input_image_point = Column(Numeric(precision=10, scale=2), comment="生成图片输入图片消耗的积分")
    output_total_point = Column(Numeric(precision=10, scale=2), comment="生成图片输出消耗的总积分")

    # 视频类模型计费
    has_reference = Column(Boolean, comment="是否有全能参考（有无参考素材）")
    video_resolution = Column(String(128), comment="视频分辨率")
    video_point = Column(Numeric(precision=10, scale=2), comment="视频每秒消耗的积分，视频类模型计费")


class AIModelReferencePoint(BasicModel):
    """
    使用了视频素材的全能参考时，视频模型最低积分消耗
    """
    __tablename__ = "ai_model_reference_point"

    model_id = Column(String(256), comment="AIModel表ID")

    video_resolution = Column(String(128), comment="视频分辨率")
    video_output_duration = Column(Integer, comment="视频输出时长（秒）")
    reference_min_duration = Column(Integer, comment="素材输入总时长低于此值时按最低消耗计")
    video_point = Column(Numeric(precision=10, scale=2), comment="视频消耗的最低积分（整个视频）")


class SuperResPoint(BasicModel):
    """
    视频超分消耗积分配置
    """
    __tablename__ = "super_res_point"

    target_video_resolution = Column(String(128), comment="视频超分目标分辨率" + SuperResResolutionType.__doc__.strip())
    point = Column(Numeric(precision=10, scale=2), comment="每秒消耗的积分数量")