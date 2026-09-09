"""通用视频生成回调处理器

供成片和短视频复用，封装回调状态分派、错误提取、视频处理等通用逻辑。
"""
from typing import Callable

from app.utils.video_processing import process_generated_video


def extract_video_url(result: dict) -> str:
    """从 Seedance 回调/查询结果中提取视频 URL"""
    url = result.get("content", {}).get("video_url")
    if not url:
        raise ValueError(f"未返回视频URL, result keys: {list(result.keys())}")
    return url


def extract_error_message(callback_data: dict) -> str:
    """从回调数据中提取错误信息"""
    error = callback_data.get("error") or callback_data.get("model_error", {})
    if isinstance(error, dict):
        return error.get("message", "视频生成失败")
    return str(error) or "视频生成失败"


class VideoCallbackHandler:
    """通用视频生成回调处理器"""

    def dispatch(
        self,
        callback_data: dict,
        on_success: Callable[[str], None],
        on_failure: Callable[[str], None],
        on_progress: Callable[[], None],
        on_queued: Callable[[], None] = None,
        on_running: Callable[[], None] = None,
    ):
        """根据回调状态分派到对应处理函数

        Args:
            callback_data: 方舟回调数据
            on_success: 成功处理函数，接收 video_url
            on_failure: 失败处理函数，接收 error_msg
            on_progress: 中间状态处理函数（未知/其他中间态兜底），无参数
            on_queued: 排队中处理函数，无参数；若未传则回落到 on_progress
            on_running: 生成中处理函数，无参数；若未传则回落到 on_progress
        """
        status = callback_data.get("status", "unknown")
        if status == "succeeded":
            video_url = extract_video_url(callback_data)
            on_success(video_url)
        elif status == "failed":
            error_msg = extract_error_message(callback_data)
            on_failure(error_msg)
        elif status == "queued":
            if on_queued is not None:
                on_queued()
            else:
                on_progress()
        elif status == "running":
            if on_running is not None:
                on_running()
            else:
                on_progress()
        else:
            on_progress()

    @staticmethod
    def process_video(video_url: str, project_id: str, user_id: str = "") -> dict:
        """下载视频、上传COS、提取封面尾帧

        返回: {
            "cos_url": str,
            "storage_key": str,
            "cover_url": str | None,
            "last_frame_url": str | None,
        }
        """
        return process_generated_video(video_url, project_id, user_id)
