"""区域相关公共工具"""
from app.enums.user import UserRegion


# 区域 → 该区域默认视频生成模型（对应 AIModel.model_name）
REGION_DEFAULT_VIDEO_MODEL = {
    UserRegion.DOMESTIC.value: "doubao-seedance-2-0-260128",
    UserRegion.OVERSEAS.value: "dreamina-seedance-2-0-260128",
}


def get_region_default_video_model(region: str) -> str:
    """获取指定区域的默认视频模型 model_name；未知区域返回空字符串"""
    return REGION_DEFAULT_VIDEO_MODEL.get(region, "")


def apply_region_volc_id(obj, region: str):
    """按当前 region 把对应区域的资产 ID 临时写入 volc_private_asset_id 字段。

    仅用于响应序列化，不持久化到数据库（接口无 commit，session 请求结束自动 rollback）。
    前端按 volc_private_asset_id 字段判断"是否已同步"，切换到国际版后需要看到 byteplus_asset_id 的值。
    """
    if region == UserRegion.OVERSEAS:
        obj.volc_private_asset_id = getattr(obj, "byteplus_asset_id", None)
