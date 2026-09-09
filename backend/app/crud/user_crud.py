from sqlalchemy.orm import Session

from app.enums.user import UserRegion
from app.models.user import User
from app.schemas.user import UserCreateSchema, UserUpdateSchema
from app.crud.base_crud import CRUDBase


class CRUDUser(CRUDBase[User, UserCreateSchema, UserUpdateSchema]):
    """
    用户CRUD操作
    """
    def __init__(self, model: type[User]):
        super().__init__(model)

    def get_by_username(
        self, *, username: str, db: Session
    ) -> User | None:
        return db.query(User).filter_by(username=username).first()

    def get_region(self, *, user_id: str | None, db: Session) -> str:
        """获取用户区域类型；user_id 为空或读取失败时回退为 DOMESTIC。

        返回值为 UserRegion 枚举的字符串值（如 "domestic"），便于直接与字符串字面量比较。
        """
        if not user_id:
            return UserRegion.DOMESTIC
        user = db.query(User).filter(User.id == user_id).first()
        return user.region if user and user.region else UserRegion.DOMESTIC


user_crud = CRUDUser(User)
