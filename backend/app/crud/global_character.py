import json
from collections import defaultdict

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app import models, schemas
from app.crud.base_crud import CRUDBase
from app.utils.tencent_cos_utils import cos_client


class CRUDGlobalCharacter(CRUDBase[models.GlobalCharacter, schemas.GlobalCharacterCreate, schemas.GlobalCharacterUpdate]):

    def get_by_owner(self, db: Session, user_id: str, owner_user_id: str):
        return self.get_queryset(db).filter(
            or_(
                self.model.owner_user_id == owner_user_id,
                and_(self.model.owner_user_id.is_(None), self.model.user_id == user_id),
            )
        ).order_by(self.model.create_time.desc())

    def validate_folder_ownership(self, db: Session, folder_id: str, user_id: str, owner_user_id: str) -> bool:
        folder = db.query(models.GlobalAssetFolder).filter(
            models.GlobalAssetFolder.id == folder_id,
            models.GlobalAssetFolder.is_deleted == False,
        ).first()
        if not folder:
            return False
        if folder.owner_user_id and folder.owner_user_id == owner_user_id:
            return True
        if not folder.owner_user_id and folder.user_id == user_id:
            return True
        return False

    def cleanup_character_voices(self, db: Session, character) -> None:
        """TODO: 百炼托管声音清理。旧代码调用 collectBailianManagedVoiceIds + cleanupUnreferencedBailianVoices。当前后端无百炼声音服务，暂为占位。"""
        pass


class CRUDGlobalCharacterAppearance(CRUDBase[models.GlobalCharacterAppearance, schemas.GlobalCharacterAppearanceCreate, schemas.GlobalCharacterAppearanceUpdate]):

    def get_by_character(self, db: Session, character_id: str):
        return self.get_queryset(db).filter(
            self.model.character_id == character_id,
        ).order_by(self.model.appearance_index.asc())

    def get_by_character_and_index(self, db: Session, character_id: str, appearance_index: int) -> models.GlobalCharacterAppearance | None:
        return self.get_queryset(db).filter(
            self.model.character_id == character_id,
            self.model.appearance_index == appearance_index,
        ).first()

    def get_next_appearance_index(self, db: Session, character_id: str) -> int:
        appearances = self.get_queryset(db).filter(
            self.model.character_id == character_id,
        ).all()
        if not appearances:
            return 0
        return max(a.appearance_index for a in appearances) + 1

    def get_batch_by_characters(self, db: Session, character_ids: list[str]) -> dict[str, list]:
        """批量查询多角色的 appearances，避免 N+1"""
        appearances = db.query(models.GlobalCharacterAppearance).filter(
            models.GlobalCharacterAppearance.is_deleted == False,
            models.GlobalCharacterAppearance.character_id.in_(character_ids),
        ).order_by(
            models.GlobalCharacterAppearance.character_id,
            models.GlobalCharacterAppearance.appearance_index.asc(),
        ).all()
        result = defaultdict(list)
        for app in appearances:
            result[app.character_id].append(app)
        return result

    def resolve_preview_url(self, appearances: list) -> str | None:
        """从主外观解析预览图 URL"""
        if not appearances:
            return None
        primary = next((a for a in appearances if a.appearance_index == 0), appearances[0])
        image_urls = json.loads(primary.image_urls) if primary.image_urls else []
        if image_urls:
            idx = primary.selected_index if primary.selected_index is not None else 0
            key = image_urls[idx] if idx < len(image_urls) else image_urls[0]
            if key:
                return cos_client.key_to_url(key)
        if primary.image_url:
            return cos_client.key_to_url(primary.image_url)
        return None

    def resolve_thumbnail_url(self, appearances: list) -> str | None:
        """从主外观解析缩略图 URL（优先按 selected_index 从 thumbnail_urls 数组选取）"""
        if not appearances:
            return None
        primary = next((a for a in appearances if a.appearance_index == 0), appearances[0])
        # 优先：从 thumbnail_urls 数组按 selected_index 选取（与 image_url 选取逻辑保持一致）
        thumb_urls = json.loads(primary.thumbnail_urls) if primary.thumbnail_urls else []
        if thumb_urls:
            idx = primary.selected_index if primary.selected_index is not None else 0
            key = thumb_urls[idx] if idx < len(thumb_urls) else thumb_urls[0]
            if key:
                return cos_client.key_to_url(key)
        # 兼容：thumbnail_url 单值字段
        if primary.thumbnail_url:
            return cos_client.key_to_url(primary.thumbnail_url)
        return None

    def update_description_at_index(self, db: Session, appearance, description: str, index: int = 0):
        """更新 descriptions JSON 数组指定位置的描述"""
        descriptions = json.loads(appearance.descriptions) if appearance.descriptions else []
        if not descriptions:
            descriptions = [appearance.description or ""]
        while len(descriptions) <= index:
            descriptions.append("")
        descriptions[index] = description
        if not descriptions[0]:
            descriptions[0] = description
        appearance.descriptions = json.dumps(descriptions)
        appearance.description = descriptions[0]
        db.add(appearance)
        db.commit()
        db.refresh(appearance)
        return appearance


global_character_crud = CRUDGlobalCharacter(models.GlobalCharacter)
global_character_appearance_crud = CRUDGlobalCharacterAppearance(models.GlobalCharacterAppearance)
