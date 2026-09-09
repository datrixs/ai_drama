"""
图片模型计费策略：按张计费

price_config:
    image_point: 每张输出图片消耗的积分
    input_point_per_piece: 输入图片每张积分（可选，首张免费）

match_config:
    is_character: 是否是生成角色图
    resolution_tier: 分辨率档位（可选，如 "low"/"high"）
"""
from decimal import Decimal

from app.core.logging import logger
from app.services.billing.base import BillingStrategy


class ImagePerPieceStrategy(BillingStrategy):
    """图片模型：按张计费（支持分辨率分档 + 输入图片计费）"""

    def estimate(self, price_config: dict, **params) -> Decimal:
        """预估 = 实际"""
        return self.calculate_actual(price_config, **params)

    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        # 输出图片费用
        output_n = params.get("n", 1)
        image_point = Decimal(str(price_config.get("image_point", 0)))
        output_point = image_point * output_n

        # 输入图片费用（首张免费，第二张起计费）
        input_point_per_piece = Decimal(str(price_config.get("input_point_per_piece", 0)))
        input_n = params.get("input_n", 0)
        billable_input_n = max(input_n - 1, 0)
        input_point = input_point_per_piece * billable_input_n

        total = output_point + input_point
        logger.info(
            f"[图片按张计费] 输出张数={output_n}, 每张={image_point}, 输出积分={output_point}, "
            f"输入张数={input_n}, 计费输入张数={billable_input_n}, 每张={input_point_per_piece}, "
            f"输入积分={input_point}, 合计={total}"
        )
        return total
