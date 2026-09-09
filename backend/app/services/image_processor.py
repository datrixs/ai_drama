import base64
import re
from io import BytesIO

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.utils.tencent_cos_utils import cos_client
from app.utils.thumbnail import upload_thumbnail

_DATA_URI_RE = re.compile(r"^data:image/(?P<ext>[a-zA-Z0-9]+);base64,(?P<data>.+)$", re.DOTALL)


def looks_like_base64(s: str) -> bool:
    """判断字符串是否为 base64 编码的图片数据（裸 base64 或 data URI）"""
    if not isinstance(s, str) or not s:
        return False
    if s.startswith("data:image/"):
        return True
    # URL 走原下载分支，不走 base64 解码
    if s.startswith(("http://", "https://")):
        return False
    # 裸 base64：仅含 base64 字符集且长度足够
    return len(s) >= 64 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", s) is not None


def decode_base64_image(s: str) -> tuple[bytes, str]:
    """解析 base64 图片数据（data URI 或裸 base64），返回 (二进制内容, 扩展名)"""
    match = _DATA_URI_RE.match(s.strip())
    if match:
        ext = match.group("ext").lower()
        ext = "jpg" if ext == "jpeg" else ext
        raw = base64.b64decode(match.group("data"))
        return raw, ext

    # 裸 base64：默认 jpg，由 PIL 探测真实格式
    cleaned = re.sub(r"\s+", "", s)
    raw = base64.b64decode(cleaned)
    ext = "jpg"
    try:
        img = Image.open(BytesIO(raw))
        if img.format:
            ext = img.format.lower().replace("jpeg", "jpg")
    except Exception:
        pass
    return raw, ext


def process_to_jpeg(data: bytes, quality: int = 90) -> bytes:
    img = Image.open(BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return buffer.read()


def add_label_bar(data: bytes, label_text: str, bar_height: int = 40) -> bytes:
    img = Image.open(BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    width, height = img.size

    canvas = Image.new("RGB", (width, height + bar_height), (50, 50, 50))
    canvas.paste(img, (0, bar_height))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("msyh.ttc", 20)
    except OSError:
        font = ImageFont.load_default()
    draw.text((10, 10), label_text, fill="white", font=font)

    buffer = BytesIO()
    canvas.save(buffer, format="JPEG", quality=90, optimize=True)
    buffer.seek(0)
    return buffer.read()


def download_and_store_image(
    image_url: str, user_id: str, key_prefix: str = "character"
) -> tuple[str, str | None]:
    """下载图片并上传到 COS，同时生成缩略图。返回 (image_key, thumbnail_key)。"""

    if looks_like_base64(image_url):
        raw, ext = decode_base64_image(image_url)
        content_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
        key = cos_client.generate_unique_key("gen", key_prefix, user_id, ext)
        cos_client.upload_object(raw, key, content_type=content_type)
        thumb_key = upload_thumbnail(raw, key)
        return key, thumb_key
    resp = httpx.get(image_url, timeout=120)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    ext_map = {"image/png": "png", "image/webp": "webp", "image/gif": "gif"}
    ext = ext_map.get(content_type.split(";")[0], "jpg")
    key = cos_client.generate_unique_key("gen", key_prefix, user_id, ext)
    cos_client.upload_object(resp.content, key, content_type=content_type or "image/jpeg")

    thumb_key = upload_thumbnail(resp.content, key)

    return key, thumb_key


def upload_image_source_to_cos(source: str, user_id: str, biz: str = "image") -> str:
    """把图片源（data URL / 裸 base64）上传到 COS 返回签名 URL。

    http(s) URL 原样透传；无法识别的格式也原样返回，由下游报错。
    用于 API 入口兜底前端漏传 COS 的本地图片。
    """
    if not source or source.startswith(("http://", "https://")):
        return source
    if not looks_like_base64(source):
        return source
    raw, ext = decode_base64_image(source)
    content_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
    key = cos_client.generate_unique_key("upload", biz, user_id, ext)
    cos_client.upload_object(raw, key, content_type=content_type)
    return cos_client.key_to_url(key)


def normalize_image_urls(
    urls: list[str] | None, user_id: str, biz: str = "image"
) -> list[str]:
    """对图片 URL 列表逐项应用 upload_image_source_to_cos，原样保留 http URL。"""
    if not urls:
        return urls or []
    return [upload_image_source_to_cos(u, user_id, biz) for u in urls]


RATIO_TO_SIZE: dict[str, str] = {
    "3:2": "2400x1600",
    "1:1": "2048x2048",
    "2:3": "1600x2400",
}


def ratio_to_size(ratio: str) -> str:
    return RATIO_TO_SIZE.get(ratio, "2400x1600")
