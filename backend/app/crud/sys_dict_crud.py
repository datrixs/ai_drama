from typing import List
from sqlalchemy.orm import Session

from app.models import SysDict
from app.schemas import SysDictCreateSchema, SysDictUpdateSchema
from app.crud.base_crud import CRUDBase


class CRUDSysDict(CRUDBase[SysDict, SysDictCreateSchema, SysDictUpdateSchema]):
    """
    数据字典 CRUD操作
    """
    def __init__(self, model: type[SysDict]):
        super().__init__(model)

    def is_exist(self, db: Session, dict_name: str, key: str):
        """
        判断数据字典的某一个键值对是否存在。（dict_name + key 确定唯一一个键值对）
        """
        sys_dict_obj = db.query(self.model).filter(self.model.dict_name == dict_name, self.model.key == key).first()
        return True if sys_dict_obj else False

    def add_item(self, db: Session, obj_in: SysDictCreateSchema):
        """添加一条记录"""
        sys_dict_obj = self.model(**obj_in.model_dump())
        db.add(sys_dict_obj)

    def get_item_list(self, db: Session, dict_name: str) -> List[SysDict]:
        """获取某个字典所有条目"""
        item_list = db.query(self.model).filter(
            self.model.dict_name == dict_name
        ).order_by(self.model.sort.asc()).all()
        return item_list

    def get_item(self, db: Session, dict_name: str, key: str, value: str) -> SysDict:
        """获取某个字典的某一条目"""
        query = db.query(self.model).filter(self.model.dict_name == dict_name)
        if key:
            query = query.filter(self.model.key == key)
        else:
            query = query.filter(self.model.value == value)

        item = query.first()

        return item

sys_dict_crud = CRUDSysDict(SysDict)
