from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """应用配置类"""
    # FastAPI 配置项
    SECRET_KEY: str = Field(env="SECRET_KEY", description="应用密钥")
    APP_NAME: str = Field(env="APP_NAME", description="应用名称")
    API_VERSION: str = Field(env="API_VERSION", description="API版本")
    API_PREFIX: str = Field(env="API_PREFIX", description="API前缀")
    BACKEND_CORS_ORIGINS: List[str] = Field(env="BACKEND_CORS_ORIGINS", description="CORS 允许的来源")

    # 数据库配置项
    DB_HOST: str = Field(env="DB_HOST", description="数据库主机")
    DB_PORT: int = Field(env="DB_PORT", description="数据库端口")
    DB_USER: str = Field(env="DB_USER", description="数据库用户名")
    DB_PASSWORD: str = Field(env="DB_PASSWORD", description="数据库密码")
    DB_NAME: str = Field(env="DB_NAME", description="数据库名称")
    DB_POOL_SIZE: int = Field(env="DB_POOL_SIZE", description="数据库连接池大小")
    DB_MAX_OVERFLOW: int = Field(env="DB_MAX_OVERFLOW", description="数据库最大溢出连接数")

    # 加密配置项
    JWT_ALGORITHM: str = Field(env="JWT_ALGORITHM", description="JWT 算法")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES", description="JWT 访问令牌最大寿命（分钟）。启用会话滑动续期后，应远大于 SESSION_IDLE_TIMEOUT_MINUTES，避免活跃用户被强制踢出")
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, env="JWT_REFRESH_TOKEN_EXPIRE_MINUTES", description="JWT 刷新令牌过期时间（分钟），默认7天（当前未启用）")
    SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=120, env="SESSION_IDLE_TIMEOUT_MINUTES", description="会话空闲超时（分钟）。用户每次请求都会刷新该 TTL，超过该时长未活动则强制下线。默认120分钟")

    # === 火山引擎 ===
    VOLC_ACCESSKEY: str = Field(default="", env="VOLC_ACCESSKEY", description="火山引擎 AccessKey")
    VOLC_SECRETKEY: str = Field(default="", env="VOLC_SECRETKEY", description="火山引擎 SecretKey")
    ARK_API_KEY: str = Field(default="", env="ARK_API_KEY", description="火山方舟默认 API Key")

    # === BytePlus（火山引擎国际版） ===
    VOLC_OVERSEA_ACCESSKEY: str = Field(default="", env="VOLC_OVERSEA_ACCESSKEY", description="BytePlus 资产库 AccessKey")
    VOLC_OVERSEA_SECRETKEY: str = Field(default="", env="VOLC_OVERSEA_SECRETKEY", description="BytePlus 资产库 SecretKey")
    BYTEPLUS_ARK_API_KEY: str = Field(default="", env="BYTEPLUS_ARK_API_KEY", description="BytePlus 方舟默认 API Key")

    # === 视频超分(AI MediaKit 画质增强) ===
    VIDEO_SUPER_RES_API_URL: str = Field(
        default="",
        env="VIDEO_SUPER_RES_API_URL",
        description="火山 AI MediaKit 视频超分 API 端点 URL",
    )
    VIDEO_SUPER_RES_API_KEY: str = Field(
        default="",
        env="VIDEO_SUPER_RES_API_KEY",
        description="火山 AI MediaKit 视频超分 API Key",
    )

    # 默认账号
    DEFAULT_USER_NAME: str = Field(env="DEFAULT_USER_NAME", description="默认账号名称")
    DEFAULT_USER_PASSWORD: str = Field(env="DEFAULT_USER_PASSWORD", description="默认账号密码")

    # 回调地址基础 URL（用于视频生成回调，如 https://api.example.com）
    CALLBACK_BASE_URL: str = Field(default="", env="CALLBACK_BASE_URL", description="回调地址基础 URL")

    # 配置文件读取设置
    # === 日志配置 ===
    LOG_LEVEL: str = Field(env="LOG_LEVEL", description="日志记录级别")
    LOG_FILE_RETENTION: str = Field(default="90 days", env="LOG_FILE_RETENTION", description="文件日志保留时长")
    LOG_FILE_MAX_SIZE: str = Field(default="50 MB", env="LOG_FILE_MAX_SIZE", description="项目日志单文件最大大小")
    LOG_DB_RETENTION_DAYS: int = Field(default=365, env="LOG_DB_RETENTION_DAYS", description="model_call_log 表保留天数")

    # === 日志 Redis 缓冲配置 ===
    LOG_REDIS_DB: int = Field(default=1, env="LOG_REDIS_DB", description="日志专用 Redis 数据库编号")
    LOG_FLUSH_INTERVAL: int = Field(default=3600, env="LOG_FLUSH_INTERVAL", description="日志刷写 Beat 保底间隔（秒），默认1小时")
    LOG_FLUSH_BATCH_SIZE: int = Field(default=500, env="LOG_FLUSH_BATCH_SIZE", description="每批最大刷写条数")
    LOG_REDIS_BUFFER_MAX: int = Field(default=10000, env="LOG_REDIS_BUFFER_MAX", description="Redis 缓冲区最大长度")
    LOG_FLUSH_THRESHOLD: int = Field(default=1, env="LOG_FLUSH_THRESHOLD", description="缓冲区条数达到阈值时立即触发 flush")

    # ===== 腾讯 COS =====
    TENCENT_COS_SECRET_ID: str = Field(env="TENCENT_COS_SECRET_ID", default="")
    TENCENT_COS_SECRET_KEY: str = Field(env="TENCENT_COS_SECRET_KEY", default="")
    TENCENT_COS_REGION: str = Field(env="TENCENT_COS_REGION", default="ap-shanghai")
    TENCENT_COS_BUCKET: str = Field(env="TENCENT_COS_BUCKET", default="")
    TENCENT_COS_DOMAIN: str = Field(env="TENCENT_COS_DOMAIN", description="腾讯COS CDN加速域名")

    # ===== Redis =====
    REDIS_HOST: str = Field(env="REDIS_HOST", default="localhost")
    REDIS_PORT: int = Field(env="REDIS_PORT", default=6379)
    REDIS_PASSWORD: str = Field(env="REDIS_PASSWORD", default="")
    REDIS_DB: int = Field(env="REDIS_DB", default=0)

    # ===== Celery =====
    CELERY_BROKER_URL: str = Field(env="CELERY_BROKER_URL", default="")
    CELERY_RESULT_BACKEND: str = Field(env="CELERY_RESULT_BACKEND", default="")

    # ===== LLM =====
    DEFAULT_ANALYSIS_MODEL: str = Field(env="DEFAULT_ANALYSIS_MODEL", default="openai/gpt-4o-mini")
    DEFAULT_ANALYSIS_API_KEY: str = Field(env="DEFAULT_ANALYSIS_API_KEY", default="")
    DEFAULT_CHARACTER_MODEL: str = Field(env="DEFAULT_CHARACTER_MODEL", default="")
    DEFAULT_CHARACTER_API_KEY: str = Field(env="DEFAULT_CHARACTER_API_KEY", default="")
    DEFAULT_EDIT_MODEL: str = Field(env="DEFAULT_EDIT_MODEL", default="")
    DEFAULT_EDIT_API_KEY: str = Field(env="DEFAULT_EDIT_API_KEY", default="")
    DEFAULT_LOCATION_MODEL: str = Field(env="DEFAULT_LOCATION_MODEL", default="")

    # ===== 图片生成 =====
    IMAGE_GENERATION_COUNT_DEFAULT: int = Field(env="IMAGE_GENERATION_COUNT_DEFAULT", default=3)
    IMAGE_GENERATION_COUNT_MAX: int = Field(env="IMAGE_GENERATION_COUNT_MAX", default=6)

    # 支付相关
    PAY_TIME_OUT: int = Field(env='PAY_TIME_OUT', default=1*60*60)  # 支付订单超时时间
    POINTS_MIN_RECHARGE: int = Field(default=10000, env="POINTS_MIN_RECHARGE", description="积分最低充值数量")
    POINTS_RECHARGE_RATIO: int = Field(default=100, env="POINTS_RECHARGE_RATIO", description="积分充值比例")
    PAY_SOURCE_IP: str = Field(env='PAY_SOURCE_IP')
    SANDPAY_RECHARGE_CALLBACK_URL: str = Field(env="SANDPAY_RECHARGE_CALLBACK_URL")  # 充值回调地址
    SANDPAY_VIP_CALLBACK_URL: str = Field(env="SANDPAY_VIP_CALLBACK_URL")  # vip购买回调地址
    SANDPAY_CUP_QRCODE_URL: str = Field(env="SANDPAY_CUP_QRCODE_URL")
    SANDPAY_QRCODE_QUERY_URL: str = Field(env="SANDPAY_QRCODE_QUERY_URL")
    SANDPAY_PAYMENT_QUERY_URL: str = Field(env="SANDPAY_PAYMENT_QUERY_URL")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=str(BACKEND_DIR / ".env"),
        extra="allow",
    )

    @property
    def SYNC_DATABASE_URI(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def LOG_REDIS_URL(self) -> str:
        """日志专用 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.LOG_REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.LOG_REDIS_DB}"

    @property
    def CELERY_BROKER(self) -> str:
        if self.CELERY_BROKER_URL:
            return self.CELERY_BROKER_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CELERY_BACKEND(self) -> str:
        if self.CELERY_RESULT_BACKEND:
            return self.CELERY_RESULT_BACKEND
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"


settings = Settings()