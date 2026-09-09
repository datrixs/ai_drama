"""
视频模型计费策略：全能参考附加费用（最低消耗兜底）

此策略处理使用了视频素材的全能参考时的积分消耗。

price_config:
    reference_min_duration: 素材输入总时长低于此值时按最低消耗计
    video_point: 视频消耗的最低积分（整个视频）

match_config:
    video_resolution: 视频分辨率
    video_output_duration: 视频输出时长

计算逻辑:
    1. 参考时长 <= reference_min_duration → 返回固定 video_point
    2. 参考时长 > reference_min_duration → 回退到 video_second 策略，按参考时长 × 每秒积分计算
"""
import math
from decimal import Decimal

from app.core.logging import logger
from app.services.billing.base import BillingStrategy


class VideoRefMinStrategy(BillingStrategy):
    """视频模型：全能参考附加费用（最低消耗兜底）"""

    def estimate(self, price_config: dict, **params) -> Decimal:
        """预估 = 实际"""
        return self.calculate_actual(price_config, **params)

    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        reference_duration = params.get("reference_duration", 0)
        reference_min_duration = price_config.get("reference_min_duration", 0)

        if reference_duration <= reference_min_duration:
            # 参考时长 <= 最低要求 → 使用固定最低积分
            total = Decimal(str(price_config["video_point"]))
            logger.info(
                f"[视频全能参考计费] 参考时长={reference_duration}秒 <= 最低要求={reference_min_duration}秒, "
                f"使用固定积分={total}"
            )
            return total
        else:
            # 参考时长 > 最低要求 → 回退到 video_second 按秒计费
            ctx = params.get("_ctx")
            if ctx is None:
                logger.warning(
                    f"[视频全能参考计费] 参考时长={reference_duration}秒 > 最低要求={reference_min_duration}秒, "
                    f"但无上下文无法回退查询, 使用固定积分={price_config['video_point']}"
                )
                return Decimal(str(price_config["video_point"]))

            from app.enums import PricingRuleType
            video_pricing = ctx.engine.match_pricing(
                db=ctx.db,
                model_id=ctx.model_id,
                rule_type=PricingRuleType.VIDEO_SECOND.value,
                match_params={
                    "has_reference": True,
                    "video_resolution": params.get("video_resolution"),
                },
            )

            if video_pricing is None:
                logger.warning(
                    f"[视频全能参考计费] 参考时长={reference_duration}秒 > 最低要求={reference_min_duration}秒, "
                    f"回退查询video_second未找到定价, 使用固定积分={price_config['video_point']}"
                )
                return Decimal(str(price_config["video_point"]))

            per_second = float(video_pricing.price_config.get("video_point_per_second", 0))
            total = Decimal(str(math.ceil(reference_duration * per_second)))
            logger.info(
                f"[视频全能参考计费] 参考时长={reference_duration}秒 > 最低要求={reference_min_duration}秒, "
                f"回退video_second计费: 每秒={per_second}, 合计={total}"
            )
            return total
