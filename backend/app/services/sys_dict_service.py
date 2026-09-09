import uuid
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.core.logging import logger
from app.schemas import SysDictCreateSchema, SysDictResponse


class SysDictService:

    @classmethod
    def add_item(
        cls,
        db: Session,
        dict_name: str,
        key: str,
        value: str,
        sort: int = 1,
        remark: str = '',
        is_commit: bool = False,
    ):
        """添加一条数据字典"""
        try:
            sys_dict_schema = SysDictCreateSchema(dict_name=dict_name, key=key, value=value, sort=sort, remark=remark)
            crud.sys_dict_crud.add_item(db, sys_dict_schema)
            logger.success(f"添加数据字典: {sys_dict_schema.dict_name}, key: {sys_dict_schema.key}, value: {sys_dict_schema.value}, sort: {sys_dict_schema.sort}, remark: {sys_dict_schema.remark}")
        except Exception as e:
            logger.error(f"添加数据字典失败，error：{e}")
            raise e
        else:
            if is_commit:
                db.commit()

    @classmethod
    def get_item_list(cls, db: Session, dict_name: str) -> List[SysDictResponse]:
        """
        获取某个字典的所有条目
        """
        sys_dict_obj_list = crud.sys_dict_crud.get_item_list(db=db, dict_name=dict_name)

        resp_list = [SysDictResponse(**obj.to_dict()) for obj in sys_dict_obj_list]
        return resp_list

    @classmethod
    def get_item(cls, db: Session, dict_name: str, key: str, value: str) -> List[SysDictResponse]:
        """
        获取某个字典的某一条数据。
        查询逻辑：dict_name + (kye or value)
        """
        sys_dict_obj_list = crud.sys_dict_crud.get_item_list(db=db, dict_name=dict_name)

        resp_list = [SysDictResponse(**obj.to_dict()) for obj in sys_dict_obj_list]
        return resp_list
