"""
资产共享关系 CRUD
"""
from typing import List
from sqlalchemy.orm import Session

from app.crud.base_crud import CRUDBase
from app.models.asset import AssetShareRelation


class AssetShareRelationCRUD(CRUDBase[AssetShareRelation, dict, dict]):
    """资产共享关系 CRUD"""

    def get_shared_asset_ids(self, db: Session, user_id: str, asset_type: str = None) -> List[str]:
        """
        获取用户被授权的资产ID列表
        
        Args:
            db: 数据库会话
            user_id: 客户端用户ID
            asset_type: 资产类型（character/location/voice），为空则返回所有类型
            
        Returns:
            资产ID列表
        """
        query = db.query(self.model.asset_id).filter(
            self.model.user_id == user_id,
            self.model.is_deleted == False,
        )
        
        if asset_type:
            query = query.filter(self.model.asset_type == asset_type)
        
        records = query.all()
        return [r.asset_id for r in records]

    def is_shared_to_user(self, db: Session, asset_id: str, user_id: str) -> bool:
        """
        检查资产是否已分享给指定用户
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            user_id: 客户端用户ID
            
        Returns:
            True表示已分享，False表示未分享
        """
        exists = (
            db.query(self.model.id)
            .filter(
                self.model.asset_id == asset_id,
                self.model.user_id == user_id,
                self.model.is_deleted == False,
            )
            .first()
        )
        return exists is not None

    def add_share(self, db: Session, asset_id: str, asset_type: str, user_id: str) -> AssetShareRelation:
        """
        添加资产分享关系
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            asset_type: 资产类型（character/location/voice）
            user_id: 客户端用户ID
            
        Returns:
            创建的分享关系对象
        """
        # 检查是否已存在
        existing = (
            db.query(self.model)
            .filter(
                self.model.asset_id == asset_id,
                self.model.asset_type == asset_type,
                self.model.user_id == user_id,
            )
            .first()
        )
        
        if existing:
            if existing.is_deleted:
                # 恢复已删除的记录
                existing.is_deleted = False
                db.commit()
                db.refresh(existing)
                return existing
            else:
                # 已存在且未删除
                return existing
        
        # 创建新记录
        obj_in = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "user_id": user_id,
        }
        return self.create(db=db, obj_in=obj_in)

    def remove_share(self, db: Session, asset_id: str, user_id: str) -> bool:
        """
        移除资产分享关系（软删除）
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            user_id: 客户端用户ID
            
        Returns:
            True表示删除成功，False表示记录不存在
        """
        relation = (
            db.query(self.model)
            .filter(
                self.model.asset_id == asset_id,
                self.model.user_id == user_id,
                self.model.is_deleted == False,
            )
            .first()
        )
        
        if not relation:
            return False
        
        relation.is_deleted = True
        db.commit()
        return True

    def get_shared_users(self, db: Session, asset_id: str) -> List[str]:
        """
        获取资产已分享给哪些用户
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            
        Returns:
            用户ID列表
        """
        records = (
            db.query(self.model.user_id)
            .filter(
                self.model.asset_id == asset_id,
                self.model.is_deleted == False,
            )
            .all()
        )
        return [r.user_id for r in records]

    def batch_add_shares(self, db: Session, asset_id: str, asset_type: str, user_ids: List[str]) -> int:
        """
        批量添加分享关系
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            asset_type: 资产类型（character/location/voice）
            user_ids: 用户ID列表
            
        Returns:
            成功添加的数量
        """
        count = 0
        for user_id in user_ids:
            self.add_share(db, asset_id, asset_type, user_id)
            count += 1
        return count

    def remove_all_shares_for_asset(self, db: Session, asset_id: str) -> int:
        """
        移除资产的所有分享关系（软删除）
        
        Args:
            db: 数据库会话
            asset_id: 资产ID
            
        Returns:
            删除的记录数量
        """
        count = (
            db.query(self.model)
            .filter(
                self.model.asset_id == asset_id,
                self.model.is_deleted == False,
            )
            .update({"is_deleted": True}, synchronize_session=False)
        )
        db.commit()
        return count


asset_share_relation_crud = AssetShareRelationCRUD(AssetShareRelation)
