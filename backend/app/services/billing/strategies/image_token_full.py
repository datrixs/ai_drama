"""
图片模型计费策略：按 token 计费（gpt-image-2 类型）

预估：根据 prompt 估算输入文字 token，根据输入图片像素面积估算图片 token，输出按固定 4200 token
实际结算：使用模型返回的真实 token 数

price_config:
    input_text_point: 每百万输入文字 token 积分
    input_image_point: 每百万输入图片 token 积分
    output_total_point: 每百万输出 token 积分
"""
import math
from decimal import Decimal

from app.core.logging import logger
from app.services.billing.base import BillingStrategy


class ImageTokenFullStrategy(BillingStrategy):
    """图片模型：按 token 计费（输入文本 + 输入图片 + 输出）"""

    def estimate(self, price_config: dict, **params) -> Decimal:
        """
        预估积分：
        - 文字输入：prompt → 估算 token → 积分
        - 图片输入：每张按像素面积比例 × 4200 token → 积分
        - 输出：固定 4200 token → 积分
        """
        prompt = params.get("prompt", "")
        image_info_list = params.get("image_info_list", [])

        # 文字输入积分
        text_point = Decimal("0")
        text_tokens = 0
        if price_config.get("input_text_point"):
            text_tokens = self._estimate_tokens(prompt)
            text_point = self._token_to_point(text_tokens, price_config["input_text_point"])

        # 图片输入积分
        image_point_total = Decimal("0")
        if image_info_list and price_config.get("input_image_point"):
            for image_info in image_info_list:
                width = image_info.get("width", 1024)
                height = image_info.get("height", 1024)
                # 图片像素面积与基准面积(1024*1024)的比例 × 4200 token
                scale = (width * height) / (1024 * 1024)
                base_token = 4200
                image_point = Decimal(str(
                    math.ceil(scale * base_token * float(price_config["input_image_point"]) / 1_000_000)
                ))
                image_point_total += image_point

        # 输出积分
        output_point = Decimal("0")
        if price_config.get("output_total_point"):
            output_token = 4200
            output_point = self._token_to_point(output_token, price_config["output_total_point"])

        total = Decimal(str(math.ceil(float(text_point + image_point_total + output_point))))
        logger.info(
            f"[图片Token预估] 文字token={text_tokens}, 文字积分={text_point}, "
            f"输入图片数={len(image_info_list)}, 图片积分={image_point_total}, "
            f"输出token=4200(固定), 输出积分={output_point}, 合计={total}"
        )
        return total

    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        """
        实际结算：使用真实 token 数
        """
        input_text_tokens = params.get("input_text_tokens", 0)
        input_image_tokens = params.get("input_image_tokens", 0)
        output_tokens = params.get("output_tokens", 0)

        input_text_points = self._token_to_point(input_text_tokens, price_config["input_text_point"])
        input_image_points = self._token_to_point(input_image_tokens, price_config["input_image_point"])
        output_points = self._token_to_point(output_tokens, price_config["output_total_point"])

        total = input_text_points + input_image_points + output_points
        logger.info(
            f"[图片Token结算] 输入文字token={input_text_tokens}, 积分={input_text_points}, "
            f"输入图片token={input_image_tokens}, 积分={input_image_points}, "
            f"输出token={output_tokens}, 积分={output_points}, 合计={total}"
        )
        return total
