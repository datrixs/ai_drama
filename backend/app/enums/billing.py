"""
计费规则类型枚举
"""
from enum import Enum


class PricingRuleType(Enum):
    """
    计费规则类型，决定使用哪个策略类
    """
    # 文本模型：按 token 计费
    TEXT_TOKEN = "text_token"

    # 图片模型：按张计费
    IMAGE_PER_PIECE = "image_per_piece"

    # 图片模型：按 token 计费（输入文本 + 输入图片 + 输出）
    IMAGE_TOKEN_FULL = "image_token_full"

    # 图片模型：按 token 计费（仅输出）
    IMAGE_TOKEN_OUTPUT = "image_token_output"

    # 视频模型：按秒计费
    VIDEO_SECOND = "video_second"

    # 视频模型：全能参考附加费用（最低消耗兜底）
    VIDEO_REF_MIN = "video_ref_min"

    # 视频超分：按秒计费（全局配置，model_id 为空）
    SUPER_RES = "super_res"
