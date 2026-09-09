"""
计费引擎：定价查询 + 策略分发

核心流程:
    match_pricing → 选择策略 → estimate/calculate_actual
"""
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from loguru import logger

from app.models import AIModelPricing
from app.services.billing.registry import STRATEGY_REGISTRY


@dataclass
class BillingContext:
    """计费上下文，供策略类回调用（如 VideoRefMinStrategy 需要回退查询 video_second 配置）"""
    db: Session
    model_id: Optional[str]
    engine: "BillingEngine"


class BillingEngine:
    """计费引擎：定价查询 + 策略分发"""

    # ==================== 定价查询 ====================

    @staticmethod
    def match_pricing(
        db: Session,
        model_id: Optional[str],
        rule_type: str,
        match_params: dict,
    ) -> Optional[AIModelPricing]:
        """
        根据 model_id + rule_type + 运行时参数 匹配定价档位

        匹配逻辑:
        1. 查询 model_id + rule_type + is_enabled 的所有记录
        2. 逐条比对 match_config 中的每个 key-value 是否与 match_params 一致
        3. 返回第一条完全匹配的记录

        Args:
            db: 数据库会话
            model_id: 模型ID（NULL表示全局配置）
            rule_type: 计费规则类型
            match_params: 运行时匹配参数（如 has_reference, video_resolution, is_character）

        Returns:
            AIModelPricing 或 None
        """
        queryset = db.query(AIModelPricing).filter(
            AIModelPricing.model_id == model_id,
            AIModelPricing.rule_type == rule_type,
            AIModelPricing.is_enabled == True,
            AIModelPricing.is_deleted == False,
        ).all()

        for pricing in queryset:
            if _match_config_matches(pricing.match_config, match_params):
                return pricing

        return None

    # ==================== 策略分发 ====================

    @staticmethod
    def estimate(
        db: Session,
        model_id: Optional[str],
        rule_type: str,
        match_params: dict,
        calc_params: dict,
    ) -> Decimal:
        """
        预估积分（用于预扣）

        Args:
            db: 数据库会话
            model_id: 模型ID
            rule_type: 计费规则类型
            match_params: 匹配维度参数
            calc_params: 计算参数（如 prompt_text, max_tokens, n, video_output_duration 等）

        Returns:
            Decimal: 预估积分
        """
        pricing = BillingEngine.match_pricing(db, model_id, rule_type, match_params)
        if not pricing:
            logger.warning(
                f"[计费引擎] 未找到定价配置: model_id={model_id} rule_type={rule_type} match={match_params}"
            )
            return Decimal("0")

        strategy = STRATEGY_REGISTRY.get(rule_type)
        if not strategy:
            logger.error(f"[计费引擎] 未知规则类型: {rule_type}")
            return Decimal("0")

        # 注入上下文（供需要回退查询的策略使用）
        ctx = BillingContext(db=db, model_id=model_id, engine=BillingEngine)
        calc_params["_ctx"] = ctx

        return strategy.estimate(pricing.price_config, **calc_params)

    @staticmethod
    def calculate_actual(
        db: Session,
        model_id: Optional[str],
        rule_type: str,
        match_params: dict,
        calc_params: dict,
    ) -> Decimal:
        """
        实际结算积分（模型调用完成后）

        Args:
            db: 数据库会话
            model_id: 模型ID
            rule_type: 计费规则类型
            match_params: 匹配维度参数
            calc_params: 计算参数

        Returns:
            Decimal: 实际消耗积分
        """
        pricing = BillingEngine.match_pricing(db, model_id, rule_type, match_params)
        if not pricing:
            logger.warning(
                f"[计费引擎] 未找到定价配置: model_id={model_id} rule_type={rule_type} match={match_params}"
            )
            return Decimal("0")

        strategy = STRATEGY_REGISTRY.get(rule_type)
        if not strategy:
            logger.error(f"[计费引擎] 未知规则类型: {rule_type}")
            return Decimal("0")

        ctx = BillingContext(db=db, model_id=model_id, engine=BillingEngine)
        calc_params["_ctx"] = ctx

        return strategy.calculate_actual(pricing.price_config, **calc_params)


def _match_config_matches(match_config: dict, match_params: dict) -> bool:
    """
    检查 match_config 中的所有维度是否与运行时参数匹配。
    match_config 中不存在的维度不参与匹配（视为通配）。

    字符串类型统一大写比较（如分辨率 "1080P" vs "1080p"）。
    """
    for key, expected in (match_config or {}).items():
        actual = match_params.get(key)
        # 统一字符串大小写敏感处理
        if isinstance(expected, str) and isinstance(actual, str):
            if expected.upper() != actual.upper():
                return False
        elif expected != actual:
            return False
    return True
