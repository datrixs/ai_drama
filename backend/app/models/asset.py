"""
全局资产中心
"""
from sqlalchemy import (
    Boolean,
    Column,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.models.base import BasicModel



class GlobalAssetFolder(BasicModel):
    """全局资产文件夹"""
    __tablename__ = "global_asset_folders"
    __table_args__ = (
        Index("ix_global_asset_folders_user_id", "user_id"),
        Index("ix_global_asset_folders_owner_user_id", "owner_user_id"),
    )

    user_id = Column(String(256), nullable=False, comment="创建者ID")
    owner_user_id = Column(String(256), nullable=True, comment="主账号ID（数据隔离）")
    name = Column(String(256), nullable=False, comment="文件夹名称")


class GlobalCharacter(BasicModel):
    """全局角色"""
    __tablename__ = "global_characters"
    __table_args__ = (
        Index("ix_global_characters_user_id", "user_id"),
        Index("ix_global_characters_owner_user_id", "owner_user_id"),
        Index("ix_global_characters_folder_id", "folder_id"),
    )

    user_id = Column(String(256), nullable=False, comment="创建者ID")
    owner_user_id = Column(String(256), nullable=True, comment="主账号ID")
    folder_id = Column(String(256), nullable=True, comment="文件夹ID")
    name = Column(String(256), nullable=False, comment="角色名称")
    aliases = Column(Text, nullable=True, comment="角色别名")
    profile_data = Column(Text, nullable=True, comment="角色profile数据JSON")
    profile_confirmed = Column(Boolean, default=False, comment="角色信息是否已确认")
    voice_id = Column(String(256), nullable=True, comment="语音ID")
    voice_type = Column(String(256), nullable=True, comment="语音类型")
    custom_voice_url = Column(Text, nullable=True, comment="自定义语音URL")
    custom_voice_media_id = Column(String(256), nullable=True, comment="自定义语音媒体对象ID")
    global_voice_id = Column(String(256), nullable=True, comment="绑定的全局音色ID")
    # 管理后台字段
    is_management_asset = Column(Boolean, default=False, comment="是否为平台资产")
    visibility = Column(String(32), default="private", comment="可见范围: public/partial/private")


class GlobalCharacterAppearance(BasicModel):
    """角色形象"""
    __tablename__ = "global_character_appearances"
    __table_args__ = (
        UniqueConstraint("character_id", "appearance_index", name="uq_character_appearance_index"),
        Index("ix_global_character_appearances_character_id", "character_id"),
    )

    character_id = Column(String(256), nullable=False, comment="角色ID")
    appearance_index = Column(Integer, nullable=False, comment="形象序号（0=主形象）")
    change_reason = Column(String(256), default="default", comment="变更原因/标签")
    art_style = Column(String(256), nullable=True, comment="艺术风格")
    image_model_system_prompt = Column(Text, nullable=True, comment="图生模型系统提示词")
    description = Column(Text, nullable=True, comment="形象描述")
    descriptions = Column(Text, nullable=True, comment="形象描述数组JSON")
    image_url = Column(Text, nullable=True, comment="当前图片URL")
    image_media_id = Column(String(256), nullable=True, comment="图片媒体对象ID")
    image_urls = Column(Text, nullable=True, comment="候选图片URL列表JSON")
    selected_index = Column(Integer, nullable=True, comment="当前选中的渲染图索引")
    thumbnail_url = Column(Text, nullable=True, comment="当前选中图的缩略图 COS key")
    thumbnail_urls = Column(Text, nullable=True, comment="候选缩略图 COS key 列表JSON（与 image_urls 一一对应）")
    previous_image_url = Column(Text, nullable=True, comment="上一次图片URL")
    previous_image_media_id = Column(String(256), nullable=True, comment="上一次图片媒体对象ID")
    previous_image_urls = Column(Text, nullable=True, comment="上一次图片URL列表JSON")
    previous_description = Column(Text, nullable=True, comment="上一次描述词")
    previous_descriptions = Column(Text, nullable=True, comment="上一次描述词数组JSON")
    volc_private_asset_id = Column(String(256), nullable=True, comment="火山私域素材ID")
    byteplus_asset_id = Column(String(256), nullable=True, comment="BytePlus 资产ID(国际版同步后获得)")
    gen_status = Column(String(32), nullable=False, default="pending", comment="生成状态: pending/generating/completed/failed")


class GlobalLocation(BasicModel):
    """全局场景"""
    __tablename__ = "global_locations"
    __table_args__ = (
        Index("ix_global_locations_user_id", "user_id"),
        Index("ix_global_locations_owner_user_id", "owner_user_id"),
        Index("ix_global_locations_folder_id", "folder_id"),
    )

    user_id = Column(String(256), nullable=False, comment="创建者ID")
    owner_user_id = Column(String(256), nullable=True, comment="主账号ID")
    folder_id = Column(String(256), nullable=True, comment="文件夹ID")
    name = Column(String(256), nullable=False, comment="场景/道具名称")
    art_style = Column(String(256), nullable=True, comment="艺术风格")
    summary = Column(Text, nullable=True, comment="简要描述")
    asset_kind = Column(String(256), default="location", comment="资产类型：location/prop")
    # 管理后台字段
    is_management_asset = Column(Boolean, default=False, comment="是否为平台资产")
    visibility = Column(String(32), default="private", comment="可见范围: public/partial/private")


class GlobalLocationImage(BasicModel):
    """场景图片"""
    __tablename__ = "global_location_images"
    __table_args__ = (
        UniqueConstraint("location_id", "image_index", name="uq_location_image_index"),
        Index("ix_global_location_images_location_id", "location_id"),
    )

    location_id = Column(String(256), nullable=False, comment="场景ID")
    image_index = Column(Integer, nullable=False, comment="图片序号")
    image_model_system_prompt = Column(Text, nullable=True, comment="图生模型系统提示词")
    description = Column(Text, nullable=True, comment="图片描述")
    available_slots = Column(Text, nullable=True, comment="可用槽位信息")
    image_url = Column(Text, nullable=True, comment="图片URL")
    image_media_id = Column(String(256), nullable=True, comment="图片媒体对象ID")
    is_selected = Column(Boolean, default=False, comment="是否为选中图片")
    thumbnail_url = Column(Text, nullable=True, comment="缩略图 COS key")
    previous_thumbnail_url = Column(Text, nullable=True, comment="上一张缩略图 COS key（用于撤销）")
    previous_image_url = Column(Text, nullable=True, comment="上一次图片URL")
    previous_image_media_id = Column(String(256), nullable=True, comment="上一次图片媒体对象ID")
    previous_description = Column(Text, nullable=True, comment="上一次描述词")
    volc_private_asset_id = Column(String(256), nullable=True, comment="火山私域素材ID")
    byteplus_asset_id = Column(String(256), nullable=True, comment="BytePlus 资产ID(国际版同步后获得)")
    gen_status = Column(String(32), nullable=False, default="pending", comment="生成状态: pending/generating/completed/failed")


class GlobalVoice(BasicModel):
    """全局音色"""
    __tablename__ = "global_voices"
    __table_args__ = (
        Index("ix_global_voices_user_id", "user_id"),
        Index("ix_global_voices_owner_user_id", "owner_user_id"),
        Index("ix_global_voices_folder_id", "folder_id"),
    )

    user_id = Column(String(256), nullable=False, comment="创建者ID")
    owner_user_id = Column(String(256), nullable=True, comment="主账号ID")
    folder_id = Column(String(256), nullable=True, comment="文件夹ID")
    name = Column(String(256), nullable=False, comment="音色名称")
    description = Column(Text, nullable=True, comment="详细描述")
    voice_id = Column(String(256), nullable=True, comment="qwen-tts voice ID")
    voice_type = Column(String(256), default="qwen-designed", comment="音色类型")
    custom_voice_url = Column(Text, nullable=True, comment="上传音频URL")
    custom_voice_media_id = Column(String(256), nullable=True, comment="上传音频媒体对象ID")
    volc_private_asset_id = Column(String(256), nullable=True, comment="火山私域素材ID")
    byteplus_asset_id = Column(String(256), nullable=True, comment="BytePlus 资产ID(国际版同步后获得)")
    voice_prompt = Column(Text, nullable=True, comment="AI设计提示词")
    gender = Column(String(32), nullable=True, comment="性别")
    language = Column(String(32), default="zh", comment="语言")
    duration = Column(Integer, nullable=True, comment="音频时长(秒)")
    # 管理后台字段
    is_management_asset = Column(Boolean, default=False, comment="是否为平台资产")
    visibility = Column(String(32), default="private", comment="可见范围: public/partial/private")


class AssetShareRelation(BasicModel):
    """资产共享关系"""
    __tablename__ = "asset_share_relations"
    __table_args__ = (
        Index("ix_asset_share_relations_asset_id", "asset_id"),
        Index("ix_asset_share_relations_user_id", "user_id"),
        Index("ix_asset_share_relations_asset_type", "asset_type"),
    )
    asset_id = Column(String(256), nullable=False, comment="资产ID")
    asset_type = Column(String(64), comment="资产类型: character/location/voice")
    user_id = Column(String(256), nullable=False, comment="客户端用户ID")
