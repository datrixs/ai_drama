"""用户相关枚举"""
from enum import Enum


class UserRegion(str, Enum):
    """用户区域类型

    - DOMESTIC：国内版（火山引擎 Volc Engine）
    - OVERSEAS：国际版（BytePlus 火山引擎国际版）
    """
    DOMESTIC = "domestic"
    OVERSEAS = "overseas"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """判断给定值是否为合法的 region"""
        return value in (cls.DOMESTIC.value, cls.OVERSEAS.value)
