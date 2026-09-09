"""
模型基类
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, String, Boolean


Base = declarative_base()


class BaseMixin:
    """
    所有表的公共字段
    """
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()), comment="主键 UUID")
    create_time = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    create_uid = Column(String(36), comment="创建人id")
    update_time = Column(DateTime, onupdate=datetime.now, comment="最近一次修改时间")
    update_uid = Column(String(36), comment="最近一次修改人id")
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    delete_time = Column(DateTime, comment="删除时间")


class BasicModel(Base, BaseMixin):
    """
    模型基类
    """
    __abstract__ = True

    def __repr__(self) -> str:
        """
        模型的字符串表示(方便输出到日志中)
        """
        fields = {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
        formatted = ", ".join(f"{k}={v!r}" for k, v in fields.items())
        return f"{self.__class__.__name__}({formatted})"

    def to_dict(self) -> dict:
        """
        将模型对象转为dict
        """
        dict_data = dict(self.__dict__)
        return dict_data
