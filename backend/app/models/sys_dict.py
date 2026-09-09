"""
数据字典
"""
from sqlalchemy import Column, Integer, String, Numeric

from app.models import BasicModel


class SysDict(BasicModel):
    """数据字典"""
    __tablename__ = "sys_dict"

    dict_name = Column(String(128), nullable=False, comment="数据字典名称")
    key = Column(String(128), nullable=False, comment="键名")
    value = Column(String(128), nullable=False, comment="键值")
    sort = Column(Integer, comment="排序")
    remark = Column(String(128), comment="备注")