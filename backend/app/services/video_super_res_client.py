"""视频超分(火山 AI MediaKit 画质增强)HTTP 客户端与回调处理器

调用方式: 直接 HTTP + Bearer Token(不走方舟 ARK SDK)。
回调结构: 与方舟 ARK 不同,在此独立设计 handler。
"""
import json
import time
from typing import Callable, Optional
from uuid import uuid4
from datetime import datetime

import httpx
from loguru import logger

from app.core.config import settings
from app.models.video_super_res import VideoSuperResTask
from app.utils.tencent_cos_utils import cos_client
from app.services.point import PointService
from app.crud.model_call_log_crud import model_call_log_crud


class VideoSuperResAPIError(Exception):
    """视频超分 API 调用异常"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"VideoSuperResAPIError [{status_code}]: {message}")


class VideoSuperResClient:
    """火山 AI MediaKit 视频超分 API 客户端

    使用 httpx 直接 POST,Authorization 头携带 Bearer Token。
    API 端点和 Key 从 .env 读取(VIDEO_SUPER_RES_API_URL / VIDEO_SUPER_RES_API_KEY)。
    """

    def __init__(self, timeout: int = 60):
        self.api_url = settings.VIDEO_SUPER_RES_API_URL
        self.api_key = settings.VIDEO_SUPER_RES_API_KEY
        self.timeout = timeout
        # 调用记录id(首次提交任务时记录)
        self.log_id = None

        if not self.api_url:
            raise RuntimeError("未配置 VIDEO_SUPER_RES_API_URL")
        if not self.api_key:
            raise RuntimeError("未配置 VIDEO_SUPER_RES_API_KEY")

    def _create_model_call_log(
        self,
        db,
        request_body: dict,
        user_id: str,
        task_id: str = None,
        estimated_point: float = 0.0,
        remaining_point: float = 0.0,
        request_id: str = None,
    ):
        """创建调用记录(复用调用方传入的 db,不再自建 session)"""
        log_id = str(uuid4())

        # 存储记录id
        self.log_id = log_id

        record = {
            "id": log_id,
            "user_id": user_id,
            "project_id": None,
            "task_id": task_id,
            "request_id": request_id,
            "model_provider": "volcengine",
            "model_name": request_body.get("model", ""),
            "endpoint": self.api_url,
            "api_key_masked": self.api_key[:3] + "***" + self.api_key[-3:] if len(self.api_key) >= 8 else "***",
            "media_type": "video",
            "input_media": None,
            "request_body": request_body,
            "point": estimated_point,
            "remaining_point": remaining_point,
            "call_time": datetime.now(),
            "create_time": datetime.now()
        }
        model_call_log = model_call_log_crud.create(db=db, create_data=record)
        db.add(model_call_log)
        db.commit()

        logger.debug(f"[超分]: 创建调用记录, record={record}")
        return log_id

    def _update_model_call_log(
        self,
        db,
        log_id: str,
        response_status: int,
        response_body: dict = None,
        error_message: str = None,
        latency_ms: int = 0,
        point: float = 0.0,
        provider_request_id: str = None,
        task_id: str = None,
    ):
        """更新调用记录(复用调用方传入的 db,不 close——由外层管理生命周期)"""
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
            if task_id:
                update_data["task_id"] = task_id

            model_call_log_crud.update(db, log_id, update_data)

            logger.debug(f"[超分] 更新model_call_log, log_id={log_id}, point={point}")
            logger.debug(f"[超分] 更新model_call_log内容：{update_data}")
        except Exception as e:
            logger.warning(f"更新模型调用日志失败: {e}")

    def submit_task(self, body: dict, user_id: str, db, callback_url: str = None, source_video_duration: int = 0) -> tuple:
        """提交超分任务,返回 (api_task_id, response_data)

        body 由 build_request_body 构造,callback_url 透传火山。
        若 body 内已包含 callback_url,则参数 callback_url 不再注入(以 body 为准)。

        Returns:
            (api_task_id, response_data):
                api_task_id: 火山返回的任务 ID,用于后续回调关联
                response_data: 火山完整响应 dict,调用方可入库审计

        Raises:
            VideoSuperResAPIError: API 调用失败(非 2xx 或业务错误码)
        """
        call_start_time = time.time()

        request_body = dict(body)
        if callback_url and "callback_url" not in request_body:
            request_body["callback_url"] = callback_url

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 打印完整请求 JSON(不含 Authorization 头,避免泄露 Token)
        logger.info(
            f"视频超分提交任务请求: url={self.api_url}\n"
            f"request_body={json.dumps(request_body, ensure_ascii=False, indent=2)}"
        )

        source_id = str(uuid4())
        # 获取目标分辨率
        target_resolution = request_body.get("resolution", "720P")
        logger.info(f"[超分] 目标分辨率: {target_resolution}，视频时长: {source_video_duration} 秒")

        # 预估所需积分
        estimated_point = PointService.calculate_super_res_point(
            db=db,
            video_duration=source_video_duration,
            video_resolution=target_resolution
        )
        user_balance = PointService.deduct_balance(db=db, user_id=user_id, amount=estimated_point, source_id=source_id, is_commit=True)
        # 添加调用记录
        self._create_model_call_log(db=db, request_body=request_body, user_id=user_id, estimated_point=estimated_point, remaining_point=user_balance.balance, request_id=source_id)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # === 测试 mock:跳过真实火山调用,直接返回固定响应 ===
                # 真实接入时:删除下面 4 行 mock,取消下一行 client.post 注释
                # resp = httpx.Response(
                #     status_code=200,
                #     json={
                #         "success": True,
                #         "task_id": "amk-tool-enhance-video-26062201",
                #         "request_id": "20260415150000F6DE4C24A6A0D94B7FF1",
                #     },
                # )
                resp = client.post(self.api_url, json=request_body, headers=headers)
            resp.raise_for_status()
            resp_data = resp.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"视频超分任务提交失败: HTTP {e.response.status_code}\n response_text={e.response.text[:2000]}"
            logger.error(error_msg)
            latency_ms = (time.time() - call_start_time)
            self._update_model_call_log(db=db, log_id=self.log_id, response_status=e.response.status_code, error_message=error_msg, latency_ms=latency_ms)
            PointService.refund(db=db, user_id=user_id, estimated_point=estimated_point, source_id=source_id)
            raise VideoSuperResAPIError(
                e.response.status_code,
                f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            ) from e
        except httpx.HTTPError as e:
            error_msg = f"视频超分 HTTP 请求失败: {e}"
            logger.error(error_msg)
            latency_ms = (time.time() - call_start_time)
            self._update_model_call_log(db=db, log_id=self.log_id, response_status=0, error_message=error_msg, latency_ms=latency_ms)
            PointService.refund(db=db, user_id=user_id, estimated_point=estimated_point, source_id=source_id)
            raise VideoSuperResAPIError(0, f"HTTP 请求失败: {e}") from e
        except ValueError as e:
            error_msg = f"视频超分响应解析为 JSON 失败: {e}\n response_text={resp.text[:2000]}"
            logger.error(error_msg)
            latency_ms = (time.time() - call_start_time)
            self._update_model_call_log(db=db, log_id=self.log_id, response_status=resp.status_code, error_message=error_msg, latency_ms=latency_ms)
            PointService.refund(db=db, user_id=user_id, estimated_point=estimated_point, source_id=source_id)
            raise VideoSuperResAPIError(resp.status_code, f"响应非 JSON: {resp.text[:500]}") from e

        # 打印完整响应 JSON
        logger.info(
            f"视频超分提交任务响应: HTTP {resp.status_code}\n"
            f"response_body={json.dumps(resp_data, ensure_ascii=False, indent=2)}"
        )

        api_task_id = self._extract_api_task_id(resp_data)
        if not api_task_id:
            logger.warning(f"视频超分响应未包含任务 ID,响应内容已见上")

            error_msg = f"响应未包含任务 ID,响应内容: {str(resp_data)[:500]}"
            latency_ms = (time.time() - call_start_time)
            self._update_model_call_log(db=db, log_id=self.log_id, response_status=resp.status_code, error_message=error_msg, latency_ms=latency_ms)
            PointService.refund(db=db, user_id=user_id, estimated_point=estimated_point, source_id=source_id)
            raise VideoSuperResAPIError(
                resp.status_code,
                error_msg
            )

        # 请求成功，更新调用记录
        latency_ms = (time.time() - call_start_time)
        self._update_model_call_log(db=db, log_id=self.log_id, response_status=200, response_body=resp_data,
                                    provider_request_id=api_task_id, task_id=api_task_id, latency_ms=latency_ms,
                                    point=estimated_point)

        logger.info(f"视频超分任务已提交: api_task_id={api_task_id}")
        return api_task_id, resp_data

    @staticmethod
    def _extract_api_task_id(resp_data: dict) -> Optional[str]:
        """从火山响应中提取任务 ID,候选字段兜底"""
        # 常见候选字段(按可能性排序)
        for path in (
            ("task_id",),
            ("id",),
            ("data", "task_id"),
            ("data", "id"),
            ("resp_data", "task_id"),
            ("result", "task_id"),
        ):
            value: object = resp_data
            for key in path:
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def build_request_body(task: VideoSuperResTask, callback_url: str = None) -> dict:
        """从 ORM task 构造火山 API 请求体(扁平结构)

        按 docs/super_res.md 真实结构构造,所有参数与 `video_url` 同级:
            video_url / tool_version / scene / resolution / resolution_limit /
            bitrate_level / fps / callback_args / callback_url / queue_id

        注意:
        - 不需要 `tool` 字段(已在 URL path `/api/v1/tools/enhance-video` 里)
        - 不需要 `parameters` 包裹(扁平下发)
        - 不需要 `content` 数组(直接 `video_url`)

        task.params 是前端透传的超分参数 JSON,字段集与火山 API 对齐:
            tool_version / scene / resolution / resolution_limit /
            bitrate_level / fps / callback_args / queue_id
        未提供(None)的字段不下发火山。
        """
        params: dict = dict(task.params or {})
        # 过滤 None 值,未提供的字段不下发火山
        parameters = {k: v for k, v in params.items() if v is not None}

        # 文档规则:resolution 与 resolution_limit 互斥。
        # 若同时存在,优先保留 resolution(丢弃 resolution_limit)。
        if parameters.get("resolution") and parameters.get("resolution_limit"):
            parameters.pop("resolution_limit", None)

        # video_url 必须使用 COS 临时签名 URL:火山服务器需在任务处理期间拉取源视频,
        # 永久 URL 在私有桶场景下会返回 403,导致任务失败。
        # is_local_upload=False(在线 URL)时原样下发,不签名。
        allow_external = not bool(task.is_local_upload)
        video_url = cos_client.to_signed(task.source_video_url, allow_external=allow_external)

        body = {"video_url": video_url}
        body.update(parameters)
        if callback_url:
            body["callback_url"] = callback_url
        return body


class VideoSuperResCallbackHandler:
    """火山超分回调处理器(独立设计,不复用 VideoCallbackHandler)

    基于真实回调样本实现的字段提取与状态判定(EventType=AIMediaKitTaskComplete):

    成功样本:
        {
            "RequestId": "...",
            "Version": "1.0",
            "EventType": "AIMediaKitTaskComplete",
            "EventTime": "2026-06-22T03:06:43Z",
            "Data": {
                "Code": "Success",
                "Message": "AIMediaKit Task Success",
                "TaskId": "amk-tool-enhance-video-555392753410",
                "Result": {
                    "duration": 4.087, "fps": 24, "resolution": "480p",
                    "tool_version": "standard",
                    "video_url": "https://...volcvideo.com/...?auth_key=..."
                },
                "QueueId": "..."
            },
            "TaskId": "amk-tool-enhance-video-555392753410"
        }

    失败样本:
        {
            "RequestId": "...",
            "Version": "1.0",
            "EventType": "AIMediaKitTaskComplete",
            "EventTime": "2026-06-22T02:33:32Z",
            "Data": {
                "Code": "Failed",
                "Message": "{\"type\":\"InternalServerError\",\"message\":\"file upload by url failed...\",\"code\":\"DownloadFileError\"}",
                "TaskId": "amk-tool-enhance-video-442634166530",
                "QueueId": "..."
            },
            "TaskId": "amk-tool-enhance-video-442634166530"
        }

    字段路径:
        - TaskId: Data.TaskId(顶层 TaskId 作为兜底)
        - 状态: Data.Code(Success/Failed)
        - 视频 URL: Data.Result.video_url(仅成功时有)
        - 错误信息: Data.Message(失败时通常是 JSON 字符串,解析后取 message)
    """

    def extract_task_id(self, callback_data: dict) -> Optional[str]:
        """从回调提取 api_task_id(规范字段:Data.TaskId,顶层 TaskId 兜底)"""
        for path in (
            ("Data", "TaskId"),
            ("TaskId",),
            ("data", "task_id"),
            ("task_id",),
        ):
            value: object = callback_data
            for key in path:
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(key)
            if value:
                return str(value)
        return None

    def extract_status(self, callback_data: dict) -> str:
        """提取并归一化状态为 succeeded / failed / processing

        判定优先级:
            1. Data.Code 显式为 Success → succeeded
            2. Data.Code 显式为 Failed → failed
            3. Data.Result.video_url 存在 → succeeded(兜底)
            4. 其他 → processing
        """
        data = callback_data.get("Data") if isinstance(callback_data.get("Data"), dict) else callback_data
        code = data.get("Code") if isinstance(data, dict) else None
        if code is not None:
            c = str(code).lower()
            if c in ("success", "succeeded", "done", "completed"):
                return "succeeded"
            if c in ("failed", "fail", "error"):
                return "failed"
            if c in ("running", "processing", "pending", "queued"):
                return "processing"

        result = data.get("Result") if isinstance(data, dict) else None
        if isinstance(result, dict) and result.get("video_url"):
            return "succeeded"

        return "processing"

    def extract_video_url(self, callback_data: dict) -> Optional[str]:
        """从回调提取超分后的视频 URL(规范字段:Data.Result.video_url)"""
        data = callback_data.get("Data") if isinstance(callback_data.get("Data"), dict) else callback_data
        result = data.get("Result") if isinstance(data, dict) else None
        if isinstance(result, dict):
            url = result.get("video_url")
            if url and isinstance(url, str):
                return url

        for path in (
            ("video_url",),
            ("output_url",),
            ("output", "video_url"),
        ):
            value: object = data if isinstance(data, dict) else {}
            for key in path:
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(key)
            if value and isinstance(value, str):
                return value
        return None

    def extract_error_message(self, callback_data: dict) -> str:
        """从回调提取错误信息(规范字段:Data.Message)

        失败时 Message 通常为 JSON 字符串:
            '{"type":"InternalServerError","message":"...","code":"DownloadFileError"}'
        解析后取 message;解析失败或非 JSON 时原样返回字符串。
        """
        data = callback_data.get("Data") if isinstance(callback_data.get("Data"), dict) else callback_data
        message = data.get("Message") if isinstance(data, dict) else None
        if not message:
            return "视频超分失败"

        if isinstance(message, str):
            stripped = message.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        return str(
                            parsed.get("message")
                            or parsed.get("msg")
                            or parsed.get("code")
                            or parsed.get("type")
                            or message
                        )
                except ValueError:
                    return message
            return message

        return str(message)

    def dispatch(
        self,
        callback_data: dict,
        on_success: Callable[[str], None],
        on_failure: Callable[[str], None],
        on_progress: Callable[[], None],
    ):
        """根据回调状态分派到对应处理函数"""
        status = self.extract_status(callback_data)
        if status == "succeeded":
            video_url = self.extract_video_url(callback_data)
            if not video_url:
                on_failure("回调未返回视频URL")
                return
            on_success(video_url)
        elif status == "failed":
            on_failure(self.extract_error_message(callback_data))
        else:
            on_progress()
