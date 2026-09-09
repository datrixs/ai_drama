import json
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.core.logging import logger
from app.core.security import get_password_hash, verify_password
from app.enums.user import UserRegion
from app.models.user import User
from app.schemas.user import UserCreateSchema, UserResponse, UserUpdateSchema
from app.services.config_reader import ConfigReader
from app.utils.region import get_region_default_video_model


def _attach_balance(db: Session, user: User) -> None:
    """用户对象添加余额属性"""
    user_balance_obj = crud.user_balance_crud.get_by_user_id(db, user.id)
    user.balance = user_balance_obj.balance if user_balance_obj else Decimal("0.00")


class UserService:

    @staticmethod
    def get_user(db: Session, user_id: str) -> UserResponse:
        user = crud.user_crud.get(id=user_id, db=db)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        _attach_balance(db, user)
        return UserResponse.model_validate(user)

    @staticmethod
    def get_user_list(
        db: Session, skip: int = 0, limit: int = 100
    ) -> list[UserResponse]:
        users = crud.user_crud.get_multi(skip=skip, limit=limit, db=db)
        for u in users:
            _attach_balance(db, u)
        return [UserResponse.model_validate(u) for u in users]

    @staticmethod
    def create_user(db: Session, user_in: UserCreateSchema) -> UserResponse:
        existing = crud.user_crud.get_by_username(username=user_in.username, db=db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在",
            )

        user = User(
            id=str(uuid.uuid4()),
            username=user_in.username,
            password_hash=get_password_hash(user_in.password),
            email=user_in.email,
            status=user_in.status,
            type=user_in.type,
            parent_user_id=user_in.parent_user_id,
            sub_user_limit=user_in.sub_user_limit,
            remark=user_in.remark,
            region=user_in.region or UserRegion.DOMESTIC,
        )
        db.add(user)
        db.flush()

        crud.user_balance_crud.init_user_balance(db=db, user_id=user.id)

        api_config = crud.user_api_config_crud.get_default_api_config(user.id)
        db.add(api_config)

        db.commit()
        db.refresh(user)

        logger.success(f"用户创建成功，用户ID：{user.id}")
        return UserResponse.model_validate(user)

    @staticmethod
    def update_user(
        db: Session, user_id: str, user_in: UserUpdateSchema
    ) -> UserResponse:
        user = crud.user_crud.get(id=user_id, db=db)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.success(f"用户更新成功，用户ID：{user.id}")
        return UserResponse.model_validate(user)

    @staticmethod
    def change_password(
        db: Session, user_id: str, old_password: str, new_password: str
    ) -> None:
        """修改当前用户密码：校验原密码、拒绝新旧相同，新密码哈希后入库。"""
        user = crud.user_crud.get(id=user_id, db=db)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if not verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="原密码不正确")

        # if verify_password(new_password, user.password_hash):
        #     raise HTTPException(status_code=400, detail="新密码不能与原密码相同")

        user.password_hash = get_password_hash(new_password)
        user.update_time = datetime.now()
        db.add(user)
        db.commit()

        logger.success(f"用户密码修改成功，用户ID：{user.id}")

    @staticmethod
    def delete_user(db: Session, user_id: str) -> None:
        user = crud.user_crud.get(id=user_id, db=db)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        crud.user_crud.remove(primary_id=user_id, db=db)
        logger.success(f"用户删除成功，用户ID：{user_id}")

    @staticmethod
    def update_region(db: Session, user_id: str, region: str) -> UserResponse:
        """更新用户区域类型（domestic/overseas）

        同步联动 video_model：
        - 若用户已在 custom_models 中开启目标区域的默认视频模型，且已配置对应厂商 API Key
          → video_model 设为目标模型
        - 否则 → video_model 置空（用户切换后生成视频时会得到「当前暂无视频生成模型」提示）

        前端在切换前会做确认提示，本接口不再做 Key 校验。
        """
        if not UserRegion.is_valid(region):
            raise HTTPException(status_code=400, detail="区域类型非法，仅支持 domestic 或 overseas")

        user = crud.user_crud.get(id=user_id, db=db)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        user.region = region

        # 同步 user_api_config
        config = crud.user_api_config_crud.get_by_user_id(user_id=user_id, db=db)
        if not config:
            config = crud.user_api_config_crud.get_default_api_config(user_id)
            db.add(config)

        # 判断目标区域的模型 + API Key 是否已配置
        target_model_name = get_region_default_video_model(region)
        resolved = ConfigReader(db).get_config(user_id)

        # custom_models 中目标模型是否 enabled
        raw_models = config.custom_models
        if isinstance(raw_models, str):
            try:
                raw_models = json.loads(raw_models)
            except (json.JSONDecodeError, TypeError):
                raw_models = []
        if not isinstance(raw_models, list):
            raw_models = []
        has_model = any(
            isinstance(m, dict) and m.get("model") == target_model_name and m.get("enabled")
            for m in raw_models
        )

        # 对应厂商 API Key 是否已配置
        if region == UserRegion.OVERSEAS.value:
            provider_info = resolved.find_provider_by_code("byteplus")
            has_api_key = bool(provider_info and provider_info.get("api_key"))
        else:
            has_api_key = bool(resolved.ark_api_key)

        # 满足条件则设默认模型，否则置空
        config.video_model = target_model_name if (has_model and has_api_key) else None

        db.add(user)
        db.add(config)
        db.commit()
        db.refresh(user)

        _attach_balance(db, user)
        logger.success(
            f"用户区域更新成功，用户ID：{user.id}，region：{region}，video_model：{config.video_model}"
        )
        return UserResponse.model_validate(user)
