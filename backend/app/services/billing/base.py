"""
计费策略基类

所有计费策略类继承 BillingStrategy，实现 estimate / calculate_actual 方法。
"""
from abc import ABC, abstractmethod
from decimal import Decimal


class BillingStrategy(ABC):
    """计费策略基类"""

    @abstractmethod
    def estimate(self, price_config: dict, **params) -> Decimal:
        """
        预估积分（用于预扣）

        Args:
            price_config: 定价参数（来自 ai_model_pricing.price_config）
            **params: 计算所需运行时参数（由 PointService 按 rule_type 约定传入）

        Returns:
            Decimal: 预估积分（向上取整）
        """
        ...

    @abstractmethod
    def calculate_actual(self, price_config: dict, **params) -> Decimal:
        """
        实际结算积分（模型调用完成后）

        对于预估=实际的场景，直接调用 estimate。

        Args:
            price_config: 定价参数
            **params: 计算所需运行时参数

        Returns:
            Decimal: 实际消耗积分（向上取整）
        """
        ...

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """
        预估文本消耗的 token 数量

        中文占比 > 50%：每字符约 1.5 token
        其他（英文为主）：每字符约 0.75 token
        """
        import math

        if not text:
            return 0

        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        chinese_ratio = chinese_chars / len(text)

        if chinese_ratio > 0.5:
            return math.ceil(len(text) * 1.5)
        return math.ceil(len(text) * 0.75)

    @staticmethod
    def _token_to_point(token: int, price_per_million) -> Decimal:
        """
        计算 token 消耗的积分，结果向上取整

        Args:
            token: token 数量
            price_per_million: 每百万 token 所需的积分
        """
        import math

        return Decimal(str(math.ceil(token * float(price_per_million) / 1_000_000)))
