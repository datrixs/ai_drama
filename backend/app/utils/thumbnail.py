from io import BytesIO

from PIL import Image

from app.core.logging import logger
from app.utils.tencent_cos_utils import cos_client

THUMB_KEY_PREFIX = "thumbs/card/"
THUMB_MAX_SIZE = (320, 320)
THUMB_QUALITY = 80


def generate_thumbnail_bytes(
    image_bytes: bytes,
    max_size: tuple[int, int] = THUMB_MAX_SIZE,
    quality: int = THUMB_QUALITY,
) -> bytes:
    img = Image.open(BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size, Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def get_thumbnail_key(original_key: str) -> str:
    return f"{THUMB_KEY_PREFIX}{original_key}"


def upload_thumbnail(image_bytes: bytes, original_key: str) -> str | None:
    """生成缩略图并上传到 COS，返回缩略图 key。失败返回 None 并记录日志。"""
    try:
        thumb_bytes = generate_thumbnail_bytes(image_bytes)
        thumb_key = get_thumbnail_key(original_key)
        cos_client.upload_object(thumb_bytes, thumb_key, content_type="image/jpeg")
        return thumb_key
    except Exception as e:
        logger.error(f"[thumbnail] 缩略图生成/上传失败: original_key={original_key}, error={e}")
        return None
