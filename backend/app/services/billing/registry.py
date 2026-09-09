"""
计费策略注册表

新增计费公式时：
1. 编写策略类
2. 在此注册
3. 在 ai_model_pricing 表插入配置数据
"""
from app.enums import PricingRuleType
from app.services.billing.strategies.text_token import TextTokenStrategy
from app.services.billing.strategies.image_per_piece import ImagePerPieceStrategy
from app.services.billing.strategies.image_token_full import ImageTokenFullStrategy
from app.services.billing.strategies.image_token_output import ImageTokenOutputStrategy
from app.services.billing.strategies.video_second import VideoSecondStrategy
from app.services.billing.strategies.video_ref_min import VideoRefMinStrategy
from app.services.billing.strategies.super_res import SuperResStrategy

STRATEGY_REGISTRY = {
    PricingRuleType.TEXT_TOKEN.value:           TextTokenStrategy(),
    PricingRuleType.IMAGE_PER_PIECE.value:      ImagePerPieceStrategy(),
    PricingRuleType.IMAGE_TOKEN_FULL.value:     ImageTokenFullStrategy(),
    PricingRuleType.IMAGE_TOKEN_OUTPUT.value:   ImageTokenOutputStrategy(),
    PricingRuleType.VIDEO_SECOND.value:         VideoSecondStrategy(),
    PricingRuleType.VIDEO_REF_MIN.value:        VideoRefMinStrategy(),
    PricingRuleType.SUPER_RES.value:            SuperResStrategy(),
}
