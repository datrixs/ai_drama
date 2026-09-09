"""
图片模型计费策略：按 token 计费（仅输出，Gemini banana 类型）

预估：输出 token 预估值取默认值 4200
实际结算：使用模型返回的真实输出 token 数

price_config:
    output_total_point: 每百万输出 token 积分
"""
from decimal import Decimal

from app.core.logging import logger
from app.services.billing.base import BillingStrategy


class ImageTokenOutputStrategy(BillingStrategy):
    """图片模型：按 token 计费（仅输出）"""

    def estimate(self, price_config: dict, **params) -> Decimal:
        """预估：输出 token 预估值取默认值 4200"""
        output_token = 4200
        total = self._token_to_point(output_token, price_config["output_total_point"])
        logger.info(
            f"[图片输出Token预估] 输出token={output_token}(固定), "
            f"每百万积分={price_config['output_total_point']}, 合计={total}"
        )
        return total

    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        """实际结算：使用真实输出 token 数"""
        output_tokens = params.get("output_tokens", 0)
        total = self._token_to_point(output_tokens, price_config["output_total_point"])
        logger.info(
            f"[图片输出Token结算] 输出token={output_tokens}, "
            f"每百万积分={price_config['output_total_point']}, 合计={total}"
        )
        return total
