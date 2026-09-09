"""
文本模型计费策略：按 token 计费

price_config:
    input_point_per_million: 每百万输入 token 积分
    output_point_per_million: 每百万输出 token 积分
"""
import math
from decimal import Decimal

from app.core.logging import logger
from app.services.billing.base import BillingStrategy


class TextTokenStrategy(BillingStrategy):
    """文本模型：按 token 计费"""

    def estimate(self, price_config: dict, **params) -> Decimal:
        """
        文本预估：根据 prompt 估算 token，使用 max_tokens 作为输出上限
        """
        prompt_text = params.get("prompt_text", "")
        max_tokens = params.get("max_tokens", 8192)

        input_tokens = self._estimate_tokens(prompt_text)

        input_point = input_tokens * float(price_config["input_point_per_million"]) / 1_000_000
        output_point = max_tokens * float(price_config["output_point_per_million"]) / 1_000_000
        total = Decimal(str(math.ceil(input_point + output_point)))
        logger.info(
            f"[文本预估] 输入token={input_tokens}, max输出token={max_tokens}, "
            f"输入积分={input_point:.4f}, 输出积分={output_point:.4f}, 合计={total}"
        )
        return total

    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        """
        文本实际结算：用真实 token 数
        """
        input_token = params.get("input_token", 0)
        output_token = params.get("output_token", 0)

        input_point = input_token * float(price_config["input_point_per_million"]) / 1_000_000
        output_point = output_token * float(price_config["output_point_per_million"]) / 1_000_000
        total = Decimal(str(math.ceil(input_point + output_point)))
        logger.info(
            f"[文本结算] 输入token={input_token}, 输出token={output_token}, "
            f"输入积分={input_point:.4f}, 输出积分={output_point:.4f}, 合计={total}"
        )
        return total
