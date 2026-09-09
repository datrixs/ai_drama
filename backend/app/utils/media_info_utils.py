"""
媒体文件元信息提取工具

从 URL / base64 / bytes 中提取图片/视频的分辨率、大小等信息，
用于 model_call_log 的 input_media / output_media 字段记录。
"""
import base64
import io
from typing import Optional

import httpx
from loguru import logger
from PIL import Image, ImageFile

# Range 请求只取前段，PIL 遇到截断数据默认抛错；打开容忍开关避免尺寸读取失败
ImageFile.LOAD_TRUNCATED_IMAGES = True


def _default_image_info(**extra) -> dict:
    """返回图片信息的默认空结构"""
    info = {"type": "image"}
    info.update(extra)
    return info


def get_image_info_from_url(url: str, timeout: int = 10) -> dict:
    """从 URL 获取图片元信息（分辨率 + 文件大小），同步版本兼容 gevent"""
    try:
        info = {"type": "image", "url": url}
        with httpx.Client(timeout=timeout) as client:
            head_resp = client.head(url, follow_redirects=True)
            content_length = head_resp.headers.get("content-length")
            if content_length:
                info["size_bytes"] = int(content_length)
                info["size_mb"] = round(int(content_length) / 1024 / 1024, 2)

            info.update(_read_dims_streaming(client, url))
        return info
    except Exception as e:
        logger.debug(f"获取图片元信息失败 url={url} error={e}")
        return _default_image_info(url=url)


def _read_dims_streaming(
    client: httpx.Client, url: str, max_bytes: int = 2 * 1024 * 1024,
) -> dict:
    """流式下载图片直到 PIL 能解析尺寸，最多读 max_bytes 字节。

    大图（如 20MB 原图）只在头部足够解析尺寸时停止，避免全量下载。
    JPEG 的 SOF 标记若被大 EXIF 顶到很靠后，固定 Range 会失败；
    流式按 chunk 累积、每次重试 PIL 解析，命中即返回。
    """
    buffer = io.BytesIO()
    with client.stream("GET", url, follow_redirects=True) as resp:
        for chunk in resp.iter_bytes(chunk_size=65536):
            buffer.write(chunk)
            try:
                buffer.seek(0)
                img = Image.open(buffer)
                return {"width": img.width, "height": img.height}
            except Exception:
                if buffer.tell() >= max_bytes:
                    raise
    raise RuntimeError("响应体为空，无法解析图片尺寸")


def get_image_info_from_base64(b64_str: str) -> dict:
    """从 base64 字符串获取图片元信息（分辨率 + 大小）"""
    try:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        raw = base64.b64decode(b64_str)
        info = {"type": "image", "size_bytes": len(raw), "size_mb": round(len(raw) / 1024 / 1024, 2)}
        img = Image.open(io.BytesIO(raw))
        info["width"] = img.width
        info["height"] = img.height
        return info
    except Exception as e:
        logger.debug(f"解析 base64 图片信息失败 error={e}")
        return _default_image_info()


def get_image_info_from_size_param(size: str, size_bytes: Optional[int] = None) -> dict:
    """从 size 参数（如 '2048x2048'）构造图片信息"""
    try:
        info = {"type": "image"}
        parts = size.lower().split("x")
        if len(parts) == 2:
            info["width"] = int(parts[0])
            info["height"] = int(parts[1])
        if size_bytes is not None:
            info["size_bytes"] = size_bytes
            info["size_mb"] = round(size_bytes / 1024 / 1024, 2)
        return info
    except Exception as e:
        logger.debug(f"解析 size 参数失败 size={size} error={e}")
        return _default_image_info()


def parse_image_gen_output(response_data: list, size: str = "") -> list:
    """从 litellm image_generation 响应的 data 列表提取输出图片信息"""
    try:
        results = []
        for item in response_data:
            info = {"type": "image"}
            try:
                if item.get("b64_json"):
                    info.update(get_image_info_from_base64(item["b64_json"]))
                elif item.get("url"):
                    info["url"] = item["url"]
                    if size:
                        info.update(get_image_info_from_size_param(size))
            except Exception:
                pass
            results.append(info)
        return results
    except Exception as e:
        logger.debug(f"解析图片生成输出失败 error={e}")
        return []


def parse_vision_input(image_urls: list) -> list:
    """从 vision 调用的图片 URL 列表构造输入媒体信息"""
    try:
        return [{"type": "image", "url": url} for url in image_urls]
    except Exception as e:
        logger.debug(f"构造 vision 输入媒体信息失败 error={e}")
        return []


def parse_video_task_input(body: dict) -> list:
    """从 Seedance 视频任务请求体提取输入媒体信息"""
    try:
        results = []
        content = body.get("content", [])
        for item in content:
            role = item.get("role", "")
            if role in ("reference_image", "reference_video", "reference_audio"):
                media_type = "video" if "video" in role else "audio" if "audio" in role else "image"
                entry = {"type": media_type, "role": role}
                if item.get("type") == "image_url":
                    entry["url"] = item.get("image_url", {}).get("url", "")
                elif item.get("type") == "video_url":
                    entry["url"] = item.get("video_url", {}).get("url", "")
                results.append(entry)
        return results
    except Exception as e:
        logger.debug(f"解析视频任务输入失败 error={e}")
        return []


def parse_video_task_output(result: dict) -> list:
    """从 Seedance 视频任务完成结果提取输出视频信息"""
    try:
        results = []
        output = result.get("output", {})
        video_url = output.get("video_url")
        if video_url:
            info = {"type": "video", "url": video_url}
            duration = output.get("duration")
            if duration is not None:
                info["duration"] = duration
                info["duration_desc"] = f"{duration}s"
            resolution = output.get("resolution") or output.get("video_resolution")
            if resolution:
                info["resolution"] = resolution
            results.append(info)
        return results
    except Exception as e:
        logger.debug(f"解析视频任务输出失败 error={e}")
        return []
