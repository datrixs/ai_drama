"""
火山引擎 Seedance 2.0 视频生成 SDK 客户端
国内基于 volcenginesdkarkruntime 封装
国际版基于 byteplussdkarkruntime 封装（接口与国内 SDK 完全一致）
"""
import json
import time
import uuid
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from loguru import logger
from volcenginesdkarkruntime import Ark
from volcenginesdkarkruntime._exceptions import ArkAPIError, ArkAPIStatusError
from byteplussdkarkruntime import Ark as ByteplusArk
from byteplussdkarkruntime._exceptions import (
    ArkAPIError as ByteplusArkAPIError,
    ArkAPIStatusError as ByteplusArkAPIStatusError,
)

from app.core.model_call_log_writer import model_call_log_writer
from app.crud.model_call_log_crud import model_call_log_crud
from app.db.session import SessionLocal
from app.enums.user import UserRegion
from app.models.short_video import ShortVideoTask
from app.services.point import PointService
from app.utils.media_info_utils import parse_video_task_input, parse_video_task_output

ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
BYTEPLUS_ARK_BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3"
DEFAULT_TIMEOUT = 60

# 海外版（BytePlus）合规要求：发送视频生成请求时，文本 prompt 末尾必须带"原创不侵权"声明
# 注：常量本身不含方括号，拼接时再按 [text] 格式包起来
OVERSEAS_TEXT_SUFFIX = "Original without infringement"

# 两个 SDK 的异常基类合集，方便 isinstance 判断
_SDK_API_ERRORS = (ArkAPIError, ByteplusArkAPIError)
_SDK_STATUS_ERRORS = (ArkAPIStatusError, ByteplusArkAPIStatusError)


def _ark_base_url(region: str = UserRegion.DOMESTIC) -> str:
    """按区域返回方舟 API base url"""
    return BYTEPLUS_ARK_BASE_URL if region == UserRegion.OVERSEAS else ARK_BASE_URL


class SeedanceAPIError(Exception):
    """Seedance API 调用异常"""

    def __init__(self, status_code: int, message: str, task_id: str = ""):
        self.status_code = status_code
        self.message = message
        self.task_id = task_id
        super().__init__(f"Seedance API Error [{status_code}]: {message} (task_id={task_id})")


def _client(
    api_key: str,
    region: str = UserRegion.DOMESTIC,
    timeout: int = DEFAULT_TIMEOUT,
    base_url: str = None,
):
    """创建方舟客户端：国内走火山 Ark SDK，国际版走 BytePlus Ark SDK

    base_url 由用户模型配置传入（ResolvedConfig.model_base_urls[model_name]）；
    未传则按 region 回退到内置常量。
    """
    resolved_base_url = base_url or _ark_base_url(region)
    if region == UserRegion.OVERSEAS:
        return ByteplusArk(base_url=resolved_base_url, api_key=api_key, timeout=timeout)
    return Ark(base_url=resolved_base_url, api_key=api_key, timeout=timeout)


def _estimate_video_point(self, body: dict) -> Decimal:
    """预估视频生成积分消耗"""
    logger.info(f"[积分预估] Seedance视频预估请求参数: {body}")

    db = SessionLocal()
    try:
        model_name = body.get("model", "")
        if not model_name:
            return Decimal("0")

        # 标志位：是否有参考视频
        has_reference = False
        content = body.get("content", [])
        for item in content:
            role = item.get("role", "")
            # 只有role为reference_video，认为有参考视频输入
            if role in ("reference_video", ):
                has_reference = True
                break

        # 标志位：参考视频时长
        if self.task_id and has_reference:
            reference_duration = self._get_reference_video_duration()
        else:
            reference_duration = 0

        video_resolution = body.get("resolution")
        video_output_duration = body.get("duration")

        logger.debug(f"[积分预估] 当前has_reference={has_reference} reference_duration={reference_duration}")
        estimated_point = PointService.estimate_point(
            db,
            model_name=model_name,
            has_reference=has_reference,
            video_resolution=video_resolution,
            video_output_duration=video_output_duration,
            reference_duration=reference_duration
        )
        logger.info(f"[积分预估] Seedance视频预估积分: {estimated_point}")
        return estimated_point
    finally:
        db.close()


def _write_model_call_log(
    method: str,
    path: str,
    request_body: dict,
    user_id: str = "system",
    project_id: str = None,
    task_id: str = None,
    estimated_point: float = 0.0,
    api_key: str = "",
    request_id: str = None,
) -> str:
    """写入模型调用日志"""
    request_id = request_id or str(uuid.uuid4())
    log_id = str(uuid.uuid4())

    input_media = parse_video_task_input(request_body) if path == "/contents/generations/tasks" else None

    record = {
        "id": log_id,
        "user_id": user_id,
        "project_id": project_id,
        "task_id": task_id,
        "request_id": request_id,
        "model_provider": "volcengine",
        "model_name": request_body.get("model", ""),
        "endpoint": f"{ARK_BASE_URL}{path}",
        "api_key_masked": api_key[:3] + "***" + api_key[-3:] if len(api_key) >= 8 else "***",
        "media_type": "video" if path == "/contents/generations/tasks" else None,
        "input_media": input_media,
        "request_body": request_body,
        "point": estimated_point,
        "call_time": datetime.now(),
        "create_time": datetime.now(),
        "_skip_auto_billing": True,
    }
    logger.debug(f"Seedance API 调用日志: 写入model_call_log, record={record}")
    model_call_log_writer._write_direct_to_pg(record)
    return log_id


def _update_model_call_log(
    log_id: str,
    response_status: int,
    response_body: dict = None,
    error_message: str = None,
    latency_ms: int = 0,
    point: float = 0.0,
    provider_request_id: str = None,
    user_id: str = "",
):
    """更新模型调用日志记录"""
    if not log_id:
        return

    db = SessionLocal()
    try:
        update_data = {
            "response_status": response_status,
            "response_body": response_body,
            "latency_ms": latency_ms,
            "point": point,
        }
        if response_status != 200:
            # 请求失败时，才需要处理 remaining_point。否则会和create_task_video中最后一个_update_model_call_log冲突
            # 根据log_id查询 model_call_log
            log = model_call_log_crud.get(db=db, record_id=log_id)
            remaining_point = log.remaining_point + log.point
            update_data["remaining_point"] = remaining_point

        if error_message:
            update_data["error_message"] = error_message
        if provider_request_id:
            update_data["provider_request_id"] = provider_request_id

        if response_status == 200 and response_body:
            output_media = parse_video_task_output(response_body)
            if output_media:
                update_data["output_media"] = output_media

        model_call_log_crud.update(db, log_id, update_data)
        logger.debug(f"Seedance API 调用日志: 更新model_call_log, log_id={log_id}, point={point}")
    except Exception as e:
        logger.warning(f"更新模型调用日志失败: {e}")
    finally:
        db.close()


def _deduct_points(self, body: dict, call_start_time: float, request_id: str) -> Decimal:
    """视频生成任务：预估积分、检查余额并扣除。保证只抛 SeedanceAPIError"""
    db = SessionLocal()
    estimated_point = Decimal(0)
    try:
        estimated_point = _estimate_video_point(self, body)
        if estimated_point > 0:
            balance = PointService.get_user_balance(db, self.user_id)
            if balance < estimated_point:
                error_msg = f"积分余额不足: 余额={balance}, 需要={estimated_point}"
                # 余额不足：直写 PG（避免 Redis 缓冲区延迟），与 dev 分支一致
                elapsed = int((time.time() - call_start_time) * 1000)
                input_media = parse_video_task_input(body)
                log_id = str(uuid.uuid4())
                record = {
                    "id": log_id,
                    "user_id": self.user_id,
                    "project_id": self.project_id,
                    "task_id": self.task_id,
                    "request_id": request_id,
                    "model_provider": "volcengine",
                    "model_name": body.get("model", ""),
                    "endpoint": f"{ARK_BASE_URL}/contents/generations/tasks",
                    "api_key_masked": self.api_key[:3] + "***" + self.api_key[-3:] if len(self.api_key) >= 8 else "***",
                    "media_type": "video",
                    "input_media": input_media,
                    "request_body": body,
                    "response_status": 402,
                    "response_body": {"error": error_msg},
                    "error_message": error_msg,
                    "latency_ms": elapsed,
                    "point": 0.0,
                    "remaining_point": float(balance),
                    "call_time": datetime.now(),
                    "create_time": datetime.now(),
                    "_skip_auto_billing": True,
                }
                model_call_log_writer._write_direct_to_pg(record)
                raise SeedanceAPIError(402, error_msg)
            PointService.deduct_balance(db, self.user_id, estimated_point, source_id=request_id)
            db.commit()
            logger.info(f"[积分扣除] Seedance视频任务扣除预估积分: user_id={self.user_id}, point={estimated_point}")
        return estimated_point
    except SeedanceAPIError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise SeedanceAPIError(500, f"积分处理失败: {e}")
    finally:
        db.close()


def _handle_sdk_error(e: Exception, call_start_time: float, log_id: str, user_id: str = "") -> SeedanceAPIError:
    """统一处理 SDK 异常，记录日志并返回 SeedanceAPIError（失败时 point=0，与 dev 分支一致）"""
    elapsed = int((time.time() - call_start_time) * 1000)

    if isinstance(e, _SDK_API_ERRORS):
        status_code = 400
        message = str(e)
        body = getattr(e, "body", None) or {"error": message}
        _update_model_call_log(log_id, status_code, body, message, elapsed, 0.0, user_id=user_id)
        return SeedanceAPIError(status_code, message)

    message = f"请求异常: {e}"
    _update_model_call_log(log_id, 400, {"error": message}, message, elapsed, 0.0, user_id=user_id)
    return SeedanceAPIError(0, message)


class SeedanceClient:
    """Seedance 2.0 视频生成客户端（国内 volcenginesdkarkruntime / 国际版 byteplussdkarkruntime）"""

    def __init__(
        self,
        api_key: str,
        user_id: str = "system",
        project_id: str = None,
        task_id: str = None,
        region: str = None,
        base_url: str = None,
    ):
        self.api_key = api_key
        self.user_id = user_id
        self.project_id = project_id
        self.task_id = task_id
        self.region = region
        # 用户模型配置的 base_url（按 model_name 从 ResolvedConfig.model_base_urls 取）；
        # 为 None 时由 _client 按 region 回退到内置常量
        self.base_url = base_url
        self.last_log_id = None

    def create_video_task(self, body: dict, callback_url: str = None) -> dict:
        """
        创建视频生成任务
        返回: {"id": task_id, "status": "queued", ...}
        """
        # 海外版：文本 prompt 末尾追加原创不侵权声明（仅当未包含时）
        self._apply_overseas_text_suffix(body)

        call_start_time = time.time()
        request_id = str(uuid.uuid4())

        logger.info(f"创建Seedance视频任务, model={body.get('model')}, duration={body.get('duration')}, callback_url={callback_url}")

        # 先扣除积分（余额不足时内部已写 402 日志）
        estimated_point = _deduct_points(self, body, call_start_time, request_id=request_id)

        # 扣除成功后写入初始日志（带实际 estimated_point，与 dev 分支一致）
        log_id = _write_model_call_log(
            "POST", "/contents/generations/tasks", body,
            self.user_id, self.project_id, self.task_id, float(estimated_point),
            api_key=self.api_key,
            request_id=request_id,
        )
        self.last_log_id = log_id

        try:
            kwargs = dict(body)
            if callback_url:
                kwargs["callback_url"] = callback_url

            api_url = f"{self.base_url or _ark_base_url(self.region)}/contents/generations/tasks"
            logger.info(f"Seedance API 请求: url={api_url}, api_key={self.api_key}, 参数={json.dumps(kwargs, ensure_ascii=False)}")
            resp = _client(self.api_key, self.region, base_url=self.base_url).content_generation.tasks.create(**kwargs)
            # 节省成本：mock 响应（正式使用时取消注释上行，注释掉下行）
            # resp = SimpleNamespace(id=f"cgt-mock-{uuid.uuid4().hex[:12]}")

            # SDK 遇到 HTTP 错误（4xx/5xx）会直接抛 ArkAPIStatusError，不会走到这里
            elapsed = int((time.time() - call_start_time) * 1000)
            resp_id = resp.id
            result = {"id": resp_id, "status": "queued"}
            _update_model_call_log(log_id, 200, result, latency_ms=elapsed, point=float(estimated_point), provider_request_id=resp_id, user_id=self.user_id)
            logger.info(f"Seedance API 响应: {json.dumps(result, ensure_ascii=False)}")
            return result
        except Exception as e:
            # SDK 异常（ArkAPIStatusError 等）→ 退还积分 + 记录日志
            if estimated_point > 0:
                try:
                    refund_db = SessionLocal()
                    PointService.refund(refund_db, self.user_id, estimated_point, source_id=request_id)
                except Exception as refund_err:
                    logger.error(f"[积分退还] 退还积分失败: user_id={self.user_id}, point={estimated_point}, error={refund_err}")
                finally:
                    refund_db.close()
            raise _handle_sdk_error(e, call_start_time, log_id, user_id=self.user_id)

    def cancel_video_task(self, ark_task_id: str) -> None:
        """取消方舟上的视频生成任务（DELETE /contents/generations/tasks/{id}）。

        仅 queued 状态可被取消；running 之后由方舟决定是否可取消，失败会抛 SDK 异常。
        本方法不涉及积分/退款（取消非独立计费事件，退款由调用方处理）。
        失败抛 SeedanceAPIError。
        """
        call_start_time = time.time()
        log_id = _write_model_call_log(
            "DELETE", f"/contents/generations/tasks/{ark_task_id}", {},
            self.user_id, self.project_id, self.task_id, 0.0,
            api_key=self.api_key,
        )
        self.last_log_id = log_id
        try:
            api_url = f"{self.base_url or _ark_base_url(self.region)}/contents/generations/tasks/{ark_task_id}"
            logger.info(f"Seedance 取消任务请求: url={api_url}, api_key={self.api_key}")
            _client(self.api_key, self.region, base_url=self.base_url) \
                .content_generation.tasks.delete(task_id=ark_task_id)
            elapsed = int((time.time() - call_start_time) * 1000)
            _update_model_call_log(
                log_id, 200, {"cancelled": True},
                latency_ms=elapsed, point=0.0,
                provider_request_id=ark_task_id, user_id=self.user_id,
            )
            logger.info(f"Seedance 任务已取消: ark_task_id={ark_task_id}")
        except Exception as e:
            raise _handle_sdk_error(e, call_start_time, log_id, user_id=self.user_id)

    def _get_reference_video_duration(self) -> int:
        """从short_video_task中获取参考视频时长"""
        db = SessionLocal()
        try:
            task = db.get(ShortVideoTask, self.task_id)

            if not task:
                logger.debug(f"[获取参考视频时长] 未找到 ShortVideoTask, task_id={self.task_id}，跳过参考视频时长查询")
                return 0

            if not task.reference_media_json:
                logger.error(f"[获取参考视频时长] short_video_task表，short_video_task_id={self.task_id}，reference_media_json为空，无法继续解析")
                logger.debug(f"[获取参考视频时长] task.reference_media_json: {task.reference_media_json}")
                return 0

            try:
                reference_media_data = json.loads(task.reference_media_json)
                videos = reference_media_data.get("videos", [])
                if not videos:
                    logger.warning(f"[获取参考视频时长] reference_media_json.video为空，无法获取参考视频时长")
                    return 0

                reference_duration = videos[0].get("duration", 0)
                if not reference_duration:
                    logger.warning(f"[获取参考视频时长] 从reference_media_json.video中解析出的duration为0，需要检查参数")
                    logger.debug(f"[获取参考视频时长] reference_media_json.video={videos}")

                return reference_duration
            except Exception as e:
                logger.error(f"[获取参考视频时长] 解析reference_media_json错误：{e}")
                return 0
        finally:
            db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def _apply_overseas_text_suffix(self, body: dict) -> None:
        """海外版合规：在 text prompt 末尾追加原创不侵权声明（已包含则跳过，避免重复）"""
        if self.region != UserRegion.OVERSEAS:
            return
        content = body.get("content") or []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                text = item.get("text") or ""
                if OVERSEAS_TEXT_SUFFIX not in text:
                    item["text"] = f"{text} [{OVERSEAS_TEXT_SUFFIX}]".strip() if text else f"[{OVERSEAS_TEXT_SUFFIX}]"
                    logger.info(f"[海外版合规] 已追加原创声明: [{OVERSEAS_TEXT_SUFFIX}]")
