"""
视频超分计费策略：按秒计费

全局配置，model_id 为 NULL。

price_config:
    point_per_second: 每秒消耗的积分

match_config:
    target_video_resolution: 视频超分目标分辨率
"""
from decimal import Decimal

from app.core.logging import logger
from app.services.billing.base import BillingStrategy


class SuperResStrategy(BillingStrategy):
    """视频超分：按秒计费"""

    def estimate(self, price_config: dict, **params) -> Decimal:
        """预估 = 实际"""
        return self.calculate_actual(price_config, **params)

    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        video_duration = params.get("video_duration", 0)
        point_per_second = float(price_config["point_per_second"])
        total = Decimal(str(video_duration)) * Decimal(str(point_per_second))
        logger.info(
            f"[视频超分计费] 时长={video_duration}秒, 每秒积分={point_per_second}, 合计={total}"
        )
        return total
