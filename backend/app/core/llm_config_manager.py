"""
大模型相关配置管理类
"""
from app.crud import ai_model_crud, user_api_config_crud
from app.models import User
from app.db.session import SessionLocal
from app.core.logging import logger


# 厂商code 和 user_api_config表中api_key存放字段名的映射
API_KEY_NAME_MAPPER = {
    "volcengine": "ark_api_key",
    "chatgpt": "jd_api_key",
}


class LLMConfigManager:
    def __init__(self):
        pass

    def get_base_url(self, model_id: str) -> str | None:
        """
        获取base_url
            - 优先从ai_model表获取base_url
            - 若ai_model表的base_url字段为空，则返回ai_provider的base_url字段

        param model_id: str. 模型ID(ai_model.id字段)
        """
        logger.info(f"[获取base_url] 正在获取{model_id}对应的base_url")

        db = SessionLocal()

        ai_model = ai_model_crud.get(db=db, id=model_id)
        if not ai_model:
            error_msg = "模型不存在，请检查ai_model表"
            logger.error(f"{error_msg}, model_id={model_id}")
            raise ValueError(error_msg)

        if ai_model.base_url:
            logger.info(f"[获取base_url] 从ai_model表获取base_url={ai_model.base_url}")
            return ai_model.base_url
        else:
            base_url = ai_model.ai_provider.base_url
            if not base_url:
                error_msg = "ai_model和ai_provider都没有配置base_url"
                logger.error(f"[获取base_url] {error_msg}，provider_code={ai_model.ai_provider.code}")
                raise ValueError(error_msg)

            logger.info(f"[获取base_url] ai_model表未配置base_url，从ai_provider表中获取base_url={base_url}")
            return base_url

    def get_api_key(self, user: User, model_id: str) -> str | None:
        """
        根据用户、模型id获取api_key
        """
        db = SessionLocal()

        ai_model = ai_model_crud.get(db=db, id=model_id)
        provider_code = ai_model.ai_provider.code
        logger.info(f"[获取api_key] 模型id={model_id}, provider_code={provider_code}")

        # 根据供应商code获取存放api_key的字段名称
        field_name = API_KEY_NAME_MAPPER.get(provider_code)

        # 获取用户配置
        user_api_config = user_api_config_crud.get_by_user_id(db=db, user_id=user.id)

        api_key = getattr(user_api_config, field_name)
        logger.info(f"[获取api_key] field_name={field_name}, api_key={api_key}")
        return api_key
