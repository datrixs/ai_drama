"""
视频模型计费策略：按秒计费

price_config:
    video_point_per_second: 每秒消耗的积分

match_config:
    has_reference: 是否有全能参考
    video_resolution: 视频分辨率（如 "480P", "1080P"）
"""
from decimal import Decimal

from app.core.logging import logger
from app.services.billing.base import BillingStrategy


class VideoSecondStrategy(BillingStrategy):
    """视频模型：按秒计费"""

    def estimate(self, price_config: dict, **params) -> Decimal:
        """预估 = 实际"""
        return self.calculate_actual(price_config, **params)

    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        video_output_duration = params.get("video_output_duration", 0)
        video_point_per_second = float(price_config["video_point_per_second"])
        total = Decimal(str(video_output_duration)) * Decimal(str(video_point_per_second))
        logger.info(
            f"[视频按秒计费] 时长={video_output_duration}秒, 每秒积分={video_point_per_second}, 合计={total}"
        )
        return total
