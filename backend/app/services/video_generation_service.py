"""视频生成业务 Service

将 Celery 任务中的业务逻辑下沉到这里，Celery 只负责编排（状态流转、异常捕获、调用 Service）。
"""
import json
import re
from decimal import Decimal

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.ws import ws_manager
from app.enums.base import WSEventType
from app.enums.user import UserRegion
from app.enums.video import StoryboardStatus
from app.crud.user_crud import user_crud
from app.models.model_call_log import ModelCallLog
from app.models.project import Project
from app.models.project_asset import Episode, Storyboard
from app.models.short_video import ShortVideoTask
from app.services.config_reader import ConfigReader
from app.services.multimodal_script_service import get_volc_asset_map
from app.services.point import PointService
from app.services.seedance_client import SeedanceClient
from app.services.seedance_task_builder import (
    apply_reference_picture_labels,
    build_episode_segment_task,
    build_single_shot_task,
    snap_to_duration_catalog,
    sum_shot_duration_hints,
)
from app.utils.tencent_cos_utils import cos_client
from app.utils.video_processing import process_generated_video
from app.services.video_callback_handler import extract_video_url


class VideoGenerationService:
    """成片视频生成业务 Service"""

    def __init__(self, db: Session, user_id: str, project_id: str = None):
        self.db = db
        self.user_id = user_id
        self.project_id = project_id
        # 读取用户区域：DOMESTIC-国内（火山引擎），OVERSEAS-国际（BytePlus）
        self.region = user_crud.get_region(user_id=user_id, db=db)

    # ------------------------------------------------------------------
    # API Key
    # ------------------------------------------------------------------
    # provider_code → ResolvedConfig 上的独立 API Key 字段（与 ModelCaller._PROVIDER_KEY_MAP 一致）
    _PROVIDER_KEY_MAP = {
        "volcengine": "ark_api_key",
        "dashscope": "qwen_api_key",
        "chatgpt": "jd_api_key",
        "deepseek": "jd_api_key",
    }

    def _resolve_api_key_for_model(self, resolved, model_name: str) -> str | None:
        """按模型名所属 provider 解析 api_key：独立字段 → custom_providers → None"""
        if not model_name or not resolved:
            return None
        # 兼容 volcengine/xxx 前缀
        actual_name = model_name.split("/", 1)[1] if "/" in model_name else model_name
        model_provider_map = getattr(resolved, "model_provider_map", None) or {}
        provider_code = model_provider_map.get(actual_name)
        if not provider_code:
            return None

        # 1. provider 对应的独立字段（如 volcengine → ark_api_key）
        key_field = self._PROVIDER_KEY_MAP.get(provider_code)
        if key_field:
            api_key = getattr(resolved, key_field, None)
            if api_key:
                return api_key

        # 2. 用户在 custom_providers 中为该 provider 单独配的 api_key
        provider_info = resolved.find_provider_by_code(provider_code)
        if provider_info:
            api_key = provider_info.get("api_key")
            if api_key:
                return api_key

        return None

    def get_ark_api_key(self, model_name: str = None) -> str:
        """获取方舟 API Key。

        优先按 model_name 在 model_provider_map 中找 provider，再按 provider 取
        对应的独立 API Key 字段或 custom_providers 中的 api_key；都没有时回退到
        resolved.ark_api_key → settings.ARK_API_KEY。
        """
        config_reader = ConfigReader(self.db)

        if self.project_id:
            project = self.db.query(Project).filter(Project.id == self.project_id).first()
            resolved = config_reader.get_project_config(self.user_id, project.config if project else None)
        else:
            resolved = config_reader.get_config(self.user_id)

        api_key = self._resolve_api_key_for_model(resolved, model_name)

        if not api_key:
            api_key = resolved.ark_api_key if resolved and resolved.ark_api_key else None

        if not api_key:
            api_key = getattr(settings, "ARK_API_KEY", None)

        if not api_key:
            raise ValueError("未配置 Ark API Key，请先在项目设置或个人配置中设置")
        return api_key

    # ------------------------------------------------------------------
    # 通知（WS 推送）
    # ------------------------------------------------------------------
    def _notify(self, event_type: str, data: dict):
        """推送项目事件到 WS"""
        ws_manager.publish_project_event(self.user_id, self.project_id, event_type, data)

    def _notify_success(self, storyboard: Storyboard, video_url: str):
        # allow_external=True：源地址（方舟 CDN）原样下发；COS 永久 URL 才转签名
        signed_url = cos_client.to_signed(video_url, allow_external=True) or video_url
        # 同步推 cover_url：回调刚到时为 None（前端会清旧封面、走 video 分支），
        # 异步任务完成后二次推送时有值（前端切回 img 显示新封面）
        cover_url = None
        if storyboard.cover_url:
            cover_url = cos_client.to_signed(storyboard.cover_url, allow_external=True) or storyboard.cover_url
        data = {
            "task_id": storyboard.id,
            "status": StoryboardStatus.VIDEO_COMPLETED,
            "progress": 100,
            "video_url": signed_url,
            "cover_url": cover_url,
            "segment_index": storyboard.segment_index,
        }
        self._notify(WSEventType.VIDEO_PROGRESS, data)

    def _notify_failure(self, storyboard: Storyboard, error_msg: str):
        data = {
            "task_id": storyboard.id,
            "status": StoryboardStatus.FAILED,
            "error": error_msg,
            "segment_index": storyboard.segment_index,
        }
        self._notify(WSEventType.VIDEO_PROGRESS, data)

    def _notify_progress(self, storyboard: Storyboard, progress: int = 10):
        data = {
            "task_id": storyboard.id,
            "status": StoryboardStatus.VIDEO_GENERATING,
            "progress": progress,
            "segment_index": storyboard.segment_index,
        }
        self._notify(WSEventType.VIDEO_PROGRESS, data)

    # ------------------------------------------------------------------
    # 请求体构建
    # ------------------------------------------------------------------
    def build_single_shot_body(self, storyboard: Storyboard, options: dict, default_model: str = None) -> dict:
        """构建单镜头视频生成请求体"""
        volc_map = get_volc_asset_map(self.db, self.project_id, region=self.region)
        raw_prompt = storyboard.video_prompt or storyboard.segment_intent or storyboard.scene_summary or ""
        text_prompt, asset_ref_ids = self._resolve_asset_refs(raw_prompt, volc_map)

        ref_images = []
        resolved_asset_ids = []
        seen = set()
        for aid in asset_ref_ids:
            url = volc_map.get(aid, "")
            if url and aid not in seen:
                ref_images.append(url)
                resolved_asset_ids.append(aid)
                seen.add(aid)

        for r in (storyboard.reference_images or []):
            if not isinstance(r, dict):
                continue
            # 若带 assetId，按 region 走 volc_map（已同步则返回 Asset://{volc_or_byteplus_id}），
            # 否则按普通 COS URL 处理
            asset_id = r.get("assetId")
            if asset_id and asset_id in volc_map:
                url = volc_map[asset_id]
                if url and url not in ref_images:
                    ref_images.append(url)
                continue
            rurl = r.get("url", "")
            if rurl and rurl not in ref_images:
                ref_images.append(self._to_signed_url(rurl))
        if storyboard.image_url:
            img = self._to_signed_url(storyboard.image_url)
            if img and img not in ref_images:
                ref_images.append(img)

        text_prompt = apply_reference_picture_labels(text_prompt, resolved_asset_ids)

        duration = options.get("duration")
        if duration is None:
            shots = storyboard.shots or []
            if shots:
                total = sum_shot_duration_hints(shots)
                duration = snap_to_duration_catalog(total)
            else:
                duration = 5

        resolved_model = options.get("model") or default_model
        if not resolved_model:
            raise ValueError("当前暂无视频生成模型，请先在设置中心配置")

        return build_single_shot_task(
            text_prompt=text_prompt,
            reference_image_urls=ref_images,
            model=resolved_model,
            resolution=options.get("resolution", "720p"),
            ratio=options.get("ratio", "16:9"),
            duration=duration,
            first_frame_url=self._to_signed_url(options.get("first_frame_url")),
            last_frame_url=self._to_signed_url(options.get("last_frame_url")),
            generate_audio=options.get("generate_audio", True),
        )

    def build_segment_body(self, episode: Episode, segment_index: int, options: dict, default_model: str = None) -> dict:
        """构建 Episode 片段视频生成请求体"""
        asset_map = get_volc_asset_map(self.db, self.project_id, region=self.region)

        first_frame = None
        if segment_index > 0:
            prev = self.db.query(Storyboard).filter(
                Storyboard.episode_id == episode.id,
                Storyboard.segment_index == segment_index - 1,
            ).first()
            if prev and prev.last_frame_url:
                first_frame = self._to_signed_url(prev.last_frame_url)

        resolved_model = options.get("model") or default_model
        if not resolved_model:
            raise ValueError("当前暂无视频生成模型，请先在设置中心配置")

        return build_episode_segment_task(
            episode_script_json=episode.script_json,
            segment_index=segment_index,
            asset_map=asset_map,
            plain_text=episode.script_plain_text,
            model=resolved_model,
            resolution=options.get("resolution", "720p"),
            ratio=options.get("ratio", "16:9"),
            duration=options.get("duration"),
            generate_audio=options.get("generate_audio", True),
            first_frame_url=first_frame or self._to_signed_url(options.get("first_frame_url")),
            last_frame_url=self._to_signed_url(options.get("last_frame_url")),
        )

    def build_short_video_body(self, task) -> dict:
        """构建短视频生成请求体"""
        assert isinstance(task, ShortVideoTask), "task 必须是 ShortVideoTask"
        content = []

        # 按 region 选择资产 ID 字段（前端 reference_media_json 中始终存为 volc_asset_id 键，
        # 后端按当前用户区域决定使用 Asset:// 哪个区域资产）
        # 首尾帧 ID 字段也按 region 区分
        ff_id = task.first_frame_byteplus_id if self.region == UserRegion.OVERSEAS else task.first_frame_volc_id
        lf_id = task.last_frame_byteplus_id if self.region == UserRegion.OVERSEAS else task.last_frame_volc_id

        if task.generation_type == "reference" and task.reference_media_json:
            try:
                ref = json.loads(task.reference_media_json)
                # 新格式：images 数组，含 url + volc_asset_id
                for item in ref.get("images", []):
                    url = item.get("url", "") if isinstance(item, dict) else item
                    volc_id = item.get("volc_asset_id") if isinstance(item, dict) else None
                    image_url = f"Asset://{volc_id}" if volc_id else self._to_signed_url(url)
                    content.append({"type": "image_url", "role": "reference_image", "image_url": {"url": image_url}})
                # 新格式：videos / audios 数组，含 url + volc_asset_id
                for item in ref.get("videos", []):
                    url = item.get("url", "") if isinstance(item, dict) else item
                    volc_id = item.get("volc_asset_id") if isinstance(item, dict) else None
                    video_url = f"Asset://{volc_id}" if volc_id else self._to_signed_url(url)
                    content.append({"type": "video_url", "role": "reference_video", "video_url": {"url": video_url}})
                for item in ref.get("audios", []):
                    url = item.get("url", "") if isinstance(item, dict) else item
                    volc_id = item.get("volc_asset_id") if isinstance(item, dict) else None
                    audio_url = f"Asset://{volc_id}" if volc_id else self._to_signed_url(url)
                    content.append({"type": "audio_url", "role": "reference_audio", "audio_url": {"url": audio_url}})
                # 旧格式兼容：imageUrls / videoUrls / audioUrls 字符串数组
                for url in ref.get("imageUrls", []):
                    content.append({"type": "image_url", "role": "reference_image", "image_url": {"url": self._to_signed_url(url)}})
                for url in ref.get("videoUrls", []):
                    content.append({"type": "video_url", "role": "reference_video", "video_url": {"url": self._to_signed_url(url)}})
                for url in ref.get("audioUrls", []):
                    content.append({"type": "audio_url", "role": "reference_audio", "audio_url": {"url": self._to_signed_url(url)}})
            except json.JSONDecodeError:
                pass

        if task.generation_type == "first_last_frame":
            if task.first_frame_url:
                ff_url = f"Asset://{ff_id}" if ff_id else self._to_signed_url(task.first_frame_url)
                content.append({"type": "image_url", "role": "first_frame", "image_url": {"url": ff_url}})
            if task.last_frame_url:
                lf_url = f"Asset://{lf_id}" if lf_id else self._to_signed_url(task.last_frame_url)
                content.append({"type": "image_url", "role": "last_frame", "image_url": {"url": lf_url}})

        if task.prompt_text:
            content.append({"type": "text", "text": task.prompt_text})

        # 视频模型：用户配置 video_model（ShortVideoTask 自身无 model 字段）
        resolved = ConfigReader(self.db).get_config(self.user_id)
        video_model = resolved.video_model if resolved else None
        if not video_model:
            raise ValueError("当前暂无视频生成模型，请先在设置中心配置")

        body = {"model": video_model, "content": content}

        if task.ratio:
            body["ratio"] = task.ratio
        if task.resolution:
            body["resolution"] = task.resolution
        if task.duration is not None:
            body["duration"] = task.duration
        if task.generate_audio is not None:
            body["generate_audio"] = task.generate_audio

        return body

    # ------------------------------------------------------------------
    # SDK 调用
    # ------------------------------------------------------------------
    def _resolve_base_url(self, model_name: str) -> str | None:
        """从用户/项目配置的 model_base_urls 中按模型名解析 base_url，未配置返回 None"""
        if not model_name:
            return None
        config_reader = ConfigReader(self.db)
        if self.project_id:
            project = self.db.query(Project).filter(Project.id == self.project_id).first()
            resolved = config_reader.get_project_config(self.user_id, project.config if project else None)
        else:
            resolved = config_reader.get_config(self.user_id)
        model_base_urls = getattr(resolved, "model_base_urls", None) or {}
        return model_base_urls.get(model_name)

    def submit_video_task(self, body: dict, callback_url: str = None, task_id: str = None) -> dict:
        """提交视频生成任务到 Seedance，返回完整响应 {id, status, ...}"""
        api_key = self.get_ark_api_key(model_name=body.get("model"))
        base_url = self._resolve_base_url(body.get("model"))
        with SeedanceClient(
            api_key,
            user_id=self.user_id,
            project_id=self.project_id,
            task_id=task_id,
            region=self.region,
            base_url=base_url,
        ) as client:
            return client.create_video_task(body, callback_url=callback_url)

    def cancel_video_task(self, ark_task_id: str, task_id: str = None, model_name: str = None) -> None:
        """取消方舟视频生成任务（按 self.region 走国内/国际版 SDK）。

        model_name 仅用于解析 api_key/base_url，可传 None 走默认 ark_api_key 与 region 内置常量。
        失败抛 SeedanceAPIError。
        """
        api_key = self.get_ark_api_key(model_name=model_name)
        base_url = self._resolve_base_url(model_name) if model_name else None
        with SeedanceClient(
            api_key,
            user_id=self.user_id,
            project_id=self.project_id,
            task_id=task_id,
            region=self.region,
            base_url=base_url,
        ) as client:
            client.cancel_video_task(ark_task_id)

    # ------------------------------------------------------------------
    # 积分结算
    # ------------------------------------------------------------------
    def _get_billing_log(self, ark_task_id: str, task_id: str = None) -> ModelCallLog | None:
        """从 model_call_log 查询本次预扣日志（取最新一条），用于结算/退款的 point 与 source_id

        过滤 point > 0：cancel_video_task 会用同一个 ark_task_id 新建一条 point=0 的日志，
        不过滤会命中它导致退款/结算失效。
        """
        q = self.db.query(ModelCallLog).filter(
            ModelCallLog.provider_request_id == ark_task_id,
            ModelCallLog.point > 0,
        )
        if task_id:
            q = q.filter(ModelCallLog.task_id == task_id)
        return q.order_by(ModelCallLog.create_time.desc()).first()

    def settle_points(self, ark_task_id: str, task_id: str = None):
        """成功回调时结算积分（视频生成实际积分等于预估积分，diff=0）"""
        log = self._get_billing_log(ark_task_id, task_id=task_id)
        if log and log.point:
            estimated = Decimal(str(log.point))
            PointService.settle(self.db, self.user_id, estimated, estimated, source_id=log.request_id)
            logger.info(f"[积分] 视频任务结算成功: user_id={self.user_id}, ark_task_id={ark_task_id}, point={estimated}")

    def refund_points(self, ark_task_id: str, task_id: str = None):
        """失败回调时退还预扣积分"""
        log = self._get_billing_log(ark_task_id, task_id=task_id)
        if log and log.point:
            estimated = Decimal(str(log.point))
            PointService.refund(self.db, self.user_id, estimated, source_id=log.request_id)
            logger.info(f"[积分] 视频任务退款成功: user_id={self.user_id}, ark_task_id={ark_task_id}, point={estimated}")

    def _update_log_on_failure(self, ark_task_id: str, error_msg: str, task_id: str = None):
        """更新 model_call_log：失败时积分置 0 并记录错误信息（与 dev 分支 wait_for_completion 一致）

        过滤 point > 0：cancel_video_task 会用同一个 ark_task_id 新建一条 point=0 的日志，
        不过滤会误把它改成 402/"视频生成失败"。
        """
        q = self.db.query(ModelCallLog).filter(
            ModelCallLog.provider_request_id == ark_task_id,
            ModelCallLog.point > 0,
        )
        if task_id:
            q = q.filter(ModelCallLog.task_id == task_id)
        log = q.order_by(ModelCallLog.create_time.desc()).first()
        if log:
            # 先更新剩余积分
            log.remaining_point += log.point
            # 再修改积分为 0
            log.point = 0
            log.error_message = f"视频生成失败: {error_msg}"[:500]
            log.response_status = 402
            self.db.commit()

    # ------------------------------------------------------------------
    # 回调处理
    # ------------------------------------------------------------------
    def handle_callback_success(self, storyboard: Storyboard, video_url: str, ark_task_id: str = None, callback_data: dict = None):
        """回调成功：立即更新状态 + 推 WS（用源地址），下载/COS/首尾帧走异步任务

        回调到达后只是把状态置为 VIDEO_COMPLETED 并把回调原始数据落到 api_response_data，
        真正的视频处理（下载→COS→首帧→尾帧）由异步任务 finalize_storyboard_video_assets 完成，
        完成后会再次推 WS 把源地址刷新为 COS 永久地址。
        """
        project_id = self.project_id
        if not project_id:
            episode = self.db.query(Episode).filter(Episode.id == storyboard.episode_id).first()
            project_id = episode.project_id if episode else None
        if not project_id:
            logger.error(f"视频回调: 无法解析 project_id, storyboard_id={storyboard.id}")
            self.handle_callback_failure(storyboard, "无法解析项目ID", ark_task_id)
            return

        # 立即标记完成 + 保存回调原文（异步任务和列表 fallback 都从此解析源地址）
        # 重新生成场景下旧的 COS 资源必须清空，否则 finalize_storyboard_video_assets
        # 的幂等判断（if storyboard.video_url: return）会误跳过，导致 DB 永远停在旧地址
        storyboard.status = StoryboardStatus.VIDEO_COMPLETED
        storyboard.ark_task_id = None
        storyboard.api_response_data = callback_data or {}
        storyboard.video_url = None
        storyboard.cover_url = None
        storyboard.last_frame_url = None
        self.db.add(storyboard)
        self.db.commit()

        if ark_task_id:
            self.settle_points(ark_task_id, task_id=storyboard.id)

        # 第一次 WS 推送：用源地址（外部 URL 不签名），前端立即播放
        self._notify_success(storyboard, video_url)
        logger.info(
            f"视频回调: segment {storyboard.segment_index} 回调成功，source_url={video_url}，触发异步上传"
        )

        # 触发异步任务：下载源视频 → 上传 COS → 提取首尾帧 → 二次推 WS
        from app.celery_tasks.video_generation import upload_storyboard_video_assets_task
        upload_storyboard_video_assets_task.delay(storyboard.id)

    def finalize_storyboard_video_assets(self, storyboard: Storyboard):
        """异步：下载源视频 → 上传 COS → 提取首尾帧 → 更新 DB → 二次推 WS

        幂等：若 storyboard.video_url 已是 COS 地址则跳过。失败由 Celery 重试 3 次。
        源地址从 storyboard.api_response_data 解析（与 short_video 一致）。
        """
        if storyboard.video_url:
            logger.info(f"[storyboard-assets] segment {storyboard.segment_index} 已有 video_url，跳过")
            return

        project_id = self.project_id
        if not project_id:
            episode = self.db.query(Episode).filter(Episode.id == storyboard.episode_id).first()
            project_id = episode.project_id if episode else None
        if not project_id:
            logger.error(f"[storyboard-assets] 无法解析 project_id, storyboard_id={storyboard.id}")
            return

        try:
            source_url = extract_video_url(storyboard.api_response_data or {})
        except ValueError as e:
            logger.warning(f"[storyboard-assets] segment {storyboard.segment_index} 解析源地址失败: {e}")
            return

        try:
            result = process_generated_video(source_url, project_id, self.user_id)
        except Exception as e:
            logger.error(
                f"[storyboard-assets] segment {storyboard.segment_index} 视频处理失败: {e}"
            )
            raise

        storyboard.video_url = result["cos_url"]
        if result.get("cover_url"):
            storyboard.cover_url = result["cover_url"]
        if result.get("last_frame_url"):
            storyboard.last_frame_url = result["last_frame_url"]
        self.db.add(storyboard)
        self.db.commit()

        # 二次 WS 推送：用 COS 签名地址刷新前端
        self._notify_success(storyboard, result["cos_url"])
        logger.info(
            f"[storyboard-assets] segment {storyboard.segment_index} 异步上传完成，"
            f"cos_url={result['cos_url']}"
        )

    def handle_callback_failure(self, storyboard: Storyboard, error_msg: str, ark_task_id: str = None):
        """回调失败：更新状态→退还积分→更新日志→通知"""
        storyboard.status = StoryboardStatus.FAILED
        storyboard.gen_error = error_msg[:500]
        storyboard.ark_task_id = None
        self.db.add(storyboard)
        self.db.commit()

        if ark_task_id:
            self.refund_points(ark_task_id, task_id=storyboard.id)
            self._update_log_on_failure(ark_task_id, error_msg, task_id=storyboard.id)

        self._notify_failure(storyboard, error_msg)
        logger.error(f"视频回调: segment {storyboard.segment_index} 失败, error={error_msg}")

    def handle_callback_progress(self, storyboard: Storyboard):
        """回调中间状态：更新进度→通知"""
        progress = min(storyboard.segment_index * 10 + 10, 90)
        self._notify_progress(storyboard, progress)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------
    def _resolve_asset_refs(self, text: str, volc_map: dict) -> tuple[str, list[str]]:
        """解析文本中的 [[name|TYPE|id]] 资产引用标记"""
        if not text:
            return text, []

        chip_pattern = re.compile(r"\[\[([^\]|]+)\|(ROLE|LOC|SCENE|PROP)\|([^\]]+)\]\]")
        matches = chip_pattern.findall(text)
        if not matches:
            return text, []

        ordered_ids = []
        seen = set()
        for _name, _type, asset_id in matches:
            if asset_id not in seen:
                ordered_ids.append(asset_id)
                seen.add(asset_id)

        cleaned = chip_pattern.sub(r"\3", text)
        return cleaned, ordered_ids

    def _to_signed_url(self, url: str) -> str:
        """将 COS key 转为签名 URL；已是 http(s) 的直接返回"""
        if not url:
            return ""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return cos_client.key_to_url(url)

    def _sign_url(self, url: str) -> str:
        """将 URL 转为带临时签名 key 的可访问地址"""
        if not url:
            return url
        key = cos_client.url_to_key(url)
        if key and key != url:
            return cos_client.get_signed_url(key)
        return url
