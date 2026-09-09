"""视频处理工具层

纯视频处理函数（下载、上传COS、提取首帧尾帧），不涉及业务状态机。
供 video_generation.py、short_video_gen.py 等共用。
"""
import os
import subprocess
import tempfile

import httpx
from loguru import logger

from app.utils.tencent_cos_utils import cos_client


def download_video(video_url: str, timeout: int = 120) -> bytes:
    """下载视频，返回二进制内容"""
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(video_url)
        resp.raise_for_status()
        return resp.content


def upload_video_to_cos(video_data: bytes, project_id: str, user_id: str = "") -> tuple[str, str]:
    """上传视频到 COS，返回 (cos_url, storage_key)"""
    storage_key = cos_client.generate_unique_key(
        f"pipixia-drama/projects/{project_id}/videos", "mp4", user_id=user_id, ext="mp4"
    )
    cos_client.upload_object(video_data, storage_key, content_type="video/mp4")
    cos_url = cos_client.get_file_url(cos_client.bucket, storage_key)
    logger.info(f"视频已上传到COS: {storage_key}")
    return cos_url, storage_key


def upload_short_video_to_cos(video_data: bytes, user_id: str = "") -> tuple[str, str]:
    """上传短视频到 COS，返回 (cos_url, storage_key)"""
    storage_key = cos_client.generate_unique_key(
        category="short-video", biz="video", user_id=user_id, ext="mp4"
    )
    cos_client.upload_object(video_data, storage_key, content_type="video/mp4")
    cos_url = cos_client.get_permanent_url(storage_key)
    logger.info(f"短视频已上传到COS: {storage_key}")
    return cos_url, storage_key


def upload_image_to_cos(image_data: bytes, project_id: str, category: str, user_id: str = "", ext: str = "jpg") -> str:
    """上传图片到 COS，返回 URL"""
    content_type = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    key = cos_client.generate_unique_key(
        f"pipixia-drama/projects/{project_id}/{category}", ext, user_id=user_id, ext=ext
    )
    cos_client.upload_object(image_data, key, content_type=content_type)
    return cos_client.get_file_url(cos_client.bucket, key)


def save_video_local(video_data: bytes) -> str:
    """将视频保存到本地临时文件，返回路径"""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()
    with open(tmp_path, "wb") as f:
        f.write(video_data)
    return tmp_path


def extract_first_frame(local_path: str) -> bytes | None:
    """从本地视频文件提取首帧，返回图片二进制数据（失败返回 None）"""
    frame_path = local_path.replace(".mp4", "_cover.jpg")
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", local_path, "-frames:v", "1", "-q:v", "2", "-ss", "0", frame_path],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0 or not os.path.exists(frame_path):
            logger.warning(f"ffmpeg 首帧提取失败: {r.stderr}")
            return None
        with open(frame_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"首帧提取异常: {e}")
        return None
    finally:
        try:
            if os.path.exists(frame_path):
                os.unlink(frame_path)
        except OSError:
            pass


def extract_last_frame(local_path: str) -> bytes | None:
    """从本地视频文件提取尾帧，返回图片二进制数据（失败返回 None）"""
    frame_path = local_path.replace(".mp4", "_lastframe.png")
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", local_path, "-frames:v", "1", "-q:v", "2", frame_path],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0 or not os.path.exists(frame_path):
            logger.warning(f"ffmpeg 尾帧提取失败: {r.stderr}")
            return None
        with open(frame_path, "rb") as f:
            return f.read()
    except Exception as e:
        logger.error(f"尾帧提取异常: {e}")
        return None
    finally:
        try:
            if os.path.exists(frame_path):
                os.unlink(frame_path)
        except OSError:
            pass


def extract_and_upload_video_cover(video_data: bytes, user_id: str) -> str | None:
    """从视频二进制提取首帧并上传 COS，返回永久 URL（失败返回 None）

    用画布 COS key 前缀（canvas/{date}/cover-{user}-{ts}-{uuid}.jpg），
    与 upload_asset 命名规则一致；失败仅告警，不抛异常。
    """
    local_path = save_video_local(video_data)
    try:
        frame_bytes = extract_first_frame(local_path)
        if not frame_bytes:
            return None
        cover_key = cos_client.generate_unique_key(
            category="canvas", biz="cover", user_id=user_id, ext="jpg",
        )
        ok = cos_client.upload_object(frame_bytes, cover_key, content_type="image/jpeg")
        if not ok:
            logger.warning(f"[cover] 封面上传失败 key={cover_key}")
            return None
        return cos_client.get_permanent_url(cover_key)
    except Exception as e:
        logger.warning(f"[cover] 视频首帧提取失败 user={user_id} err={e}")
        return None
    finally:
        try:
            if os.path.exists(local_path):
                os.unlink(local_path)
        except OSError:
            pass


def process_generated_video(
    video_url: str, project_id: str, user_id: str = ""
) -> dict:
    """
    一站式处理生成的视频：
    1. 下载视频
    2. 上传 COS
    3. 提取首帧（封面）
    4. 提取尾帧
    5. 清理本地临时文件

    返回: {
        "cos_url": str,
        "storage_key": str,
        "cover_url": str | None,
        "last_frame_url": str | None,
    }
    """
    video_data = download_video(video_url)
    cos_url, storage_key = upload_video_to_cos(video_data, project_id, user_id)
    local_path = save_video_local(video_data)

    try:
        cover_data = extract_first_frame(local_path)
        cover_url = upload_image_to_cos(cover_data, project_id, "covers", user_id, "jpg") if cover_data else None

        last_frame_data = extract_last_frame(local_path)
        last_frame_url = upload_image_to_cos(last_frame_data, project_id, "frames", user_id, "png") if last_frame_data else None

        return {
            "cos_url": cos_url,
            "storage_key": storage_key,
            "cover_url": cover_url,
            "last_frame_url": last_frame_url,
        }
    finally:
        try:
            if os.path.exists(local_path):
                os.unlink(local_path)
        except OSError:
            pass
