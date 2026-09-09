from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    user,
    sub_user,
    user_api_config,
    ai_model,
    ai_provider,
    asset_hub,
    character_ai,
    sys_dict,
    project,
    project_analyze,
    project_log,
    model_call_log,
    project_asset,
    episode,
    ws,
    storyboard,
    video_generation,
    conversation,
    volc_asset,
    short_video,
    transfer,
    membership,
    pay_order,
    pay_callback,
    point,
    video_super_res,
    canvas,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(user.router, prefix="/user", tags=["用户"])
api_router.include_router(sub_user.router, prefix="/sub-users", tags=["子账号管理"])
api_router.include_router(user_api_config.router, prefix="/user-api-config", tags=["用户API配置"])
api_router.include_router(ai_model.router, prefix="/models", tags=["AI模型"])
api_router.include_router(ai_provider.router, prefix="/ai-providers", tags=["AI供应商"])
api_router.include_router(asset_hub.router, prefix="/asset-hub", tags=["资产中心"])
api_router.include_router(character_ai.router, prefix="/asset-hub", tags=["角色AI"])
api_router.include_router(sys_dict.router, prefix="/sys_dict", tags=["数据字典"])
api_router.include_router(project_analyze.router, prefix="/projects", tags=["剧情分析"])
api_router.include_router(project.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(project_log.router, prefix="/projects", tags=["项目日志"])
api_router.include_router(model_call_log.router, prefix="/model-call-logs", tags=["扣费记录"])
api_router.include_router(project_asset.router, prefix="/projects", tags=["项目资产库"])
# api_router.include_router(project_asset.router, prefix="/projects", tags=["项目资产库"])
api_router.include_router(project.router, prefix="/projects", tags=["短剧Agent"])
# api_router.include_router(upload.router, prefix="/upload", tags=["短剧Agent"])
# api_router.include_router(ai_expand.router, prefix="/ai_expand", tags=["短剧Agent"])
api_router.include_router(episode.router, prefix="/episodes", tags=["剧集"])
api_router.include_router(storyboard.router, prefix="/storyboard", tags=["分镜"])
api_router.include_router(video_generation.router, prefix="/video", tags=["视频生成"])
api_router.include_router(conversation.router, prefix="/conversation", tags=["对话记录"])
api_router.include_router(volc_asset.router, prefix="/volc", tags=["火山引擎"])
api_router.include_router(short_video.router, prefix="/short-video", tags=["短视频"])
api_router.include_router(video_super_res.router, prefix="/super-resolution", tags=["视频超分"])
api_router.include_router(transfer.router, prefix="/transfers", tags=["积分转账"])
api_router.include_router(membership.router, prefix="/membership", tags=["会员"])
api_router.include_router(pay_order.router, prefix="/pay-orders", tags=["支付订单"])
api_router.include_router(pay_callback.router, prefix="/pay-callback", tags=["支付回调"])
api_router.include_router(point.router, prefix="/points", tags=["积分"])
# api_router.include_router(log.router, tags=["日志"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(canvas.router, prefix="/canvas", tags=["无限画布"])
