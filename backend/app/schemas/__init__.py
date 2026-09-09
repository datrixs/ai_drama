from app.schemas.base import Msg, PageMsg, PageBase, SchemaBase  # noqa: F401
from app.schemas.auth import Token  # noqa: F401

from app.schemas.asset import (  # noqa: F401
    GlobalAssetFolderCreate, GlobalAssetFolderUpdate,
    GlobalAssetFolderItem, GlobalAssetFolderMsg, GlobalAssetFolderPageMsg,
    GlobalCharacterCreate, GlobalCharacterUpdate,
    GlobalCharacterItem, GlobalCharacterMsg, GlobalCharacterPageMsg,
    GlobalCharacterCreateResultItem, GlobalCharacterCreateMsg,
    GlobalCharacterDetailItem, GlobalCharacterDetailMsg,
    GlobalCharacterAppearanceCreate, GlobalCharacterAppearanceUpdate,
    GlobalCharacterAppearanceItem, GlobalCharacterAppearanceMsg, GlobalCharacterAppearancePageMsg,
    GlobalLocationCreate, GlobalLocationUpdate,
    GlobalLocationItem, GlobalLocationMsg, GlobalLocationPageMsg,
    GlobalLocationImageCreate, GlobalLocationImageUpdate,
    GlobalLocationImageItem, GlobalLocationImageMsg, GlobalLocationImagePageMsg,
    GlobalVoiceCreate, GlobalVoiceUpdate,
    GlobalVoiceItem, GlobalVoiceMsg, GlobalVoicePageMsg,  # noqa: F401
    GlobalAssetFolderPageParams,
    GlobalCharacterPageParams,
    GlobalCharacterAppearancePageParams,
    GlobalLocationPageParams,
    GlobalLocationImagePageParams,
    GlobalVoicePageParams,
    SelectImageRequest, UndoImageRequest, VoiceSettingsUpdate,
    UploadImageResultItem, UploadImageMsg,
    VoiceUploadResultItem, VoiceUploadMsg,
    VoiceDesignRequest,
    PickerMsg, PickerCharacterItem, PickerLocationItem, PickerVoiceItem,
    UploadTempMsg, UploadTempRequest, UploadTempResultItem,
    UploadCredentialRequest, UploadCredentialResult, UploadCredentialMsg,
    AssetType, GenerateImageRequest,
)
"""This file contains the schemas for the application."""

from .auth import Token
from .user import UserCreateSchema, UserUpdateSchema, UserResponse
from .user_balance import UserBalanceUpdateSchema, UserBalanceCreateSchema
from .user_api_config import UserApiConfigSchema, UserApiConfigCreateSchema, UserApiConfigUpdateSchema
from .sys_dict import SysDictCreateSchema, SysDictUpdateSchema, SysDictResponse
from .ai_provider import AIProviderCreateSchema, AIProviderUpdateSchema
from .model_call_log import (
    ModelCallLogPageParams,
    ModelCallLogItem, ModelCallLogDetailItem,
    ModelCallLogMsg, ModelCallLogPageMsg,
    ModelCallLogSummaryItem,
    ModelCallLogSummaryMsg,
)
from .ai_model import (AIModelCreateSchema, AIModelUpdateSchema, AIModelPointCreateSchema, AIModelPointUpdateSchema,
                       AIModelReferencePointCreateSchema, AIModelReferencePointUpdateSchema)
from .super_res_point import SuperResPointCreateSchema, SuperResPointUpdateSchema
from .ai_model_pricing import AIModelPricingCreateSchema, AIModelPricingUpdateSchema


__all__ = [
    # auth
    "Token",
    # user
    "UserCreateSchema", "UserUpdateSchema", "UserResponse",
    # user_balance
    "UserBalanceUpdateSchema", "UserBalanceCreateSchema",
    # user_api_config
    "UserApiConfigSchema", "UserApiConfigCreateSchema", "UserApiConfigUpdateSchema",
    # sys_dict
    "SysDictCreateSchema", "SysDictUpdateSchema", "SysDictResponse",
    # ai_provider
    "AIProviderCreateSchema", "AIProviderUpdateSchema",
    # model_call_log
    "ModelCallLogPageParams",
    "ModelCallLogItem", "ModelCallLogDetailItem",
    "ModelCallLogMsg", "ModelCallLogPageMsg",
    "ModelCallLogSummaryItem",
    "ModelCallLogSummaryMsg",
]
