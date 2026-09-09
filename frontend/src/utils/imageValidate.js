/**
 * 图片上传校验工具
 * 校验规则参照短视频生成页面（EditorBar.vue）的火山引擎素材约束
 */
import { isHeicFile, convertHeicToJpegFile } from '@/utils/cosUpload'

// 图片允许的格式 & 大小限制
const IMAGE_FORMATS = {
  exts: ['.jpeg', '.jpg', '.png', '.webp', '.bmp', '.tiff', '.gif', '.heic', '.heif'],
  maxSize: 30 * 1024 * 1024, // 30MB
  maxFileNameLength: 64,
}

// 火山引擎素材约束（与 EditorBar MEDIA_CONSTRAINTS.image 一致）
const IMAGE_CONSTRAINTS = {
  aspectMin: 0.4,
  aspectMax: 2.5,
  dimMin: 300,
  dimMax: 6000,
}

/**
 * 获取图片元数据（宽高）
 * HEIC/HEIF 在多数浏览器无法解码，返回 dimensionReadable:false，校验阶段跳过尺寸检查由后端兜底
 */
function getImageMetadata(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve({ width: null, height: null, dimensionReadable: false })
    }
    img.src = url
  })
}

/**
 * 校验图片文件，返回 { valid, error, file }
 * - valid: boolean
 * - error: 失败原因文案（valid=false 时有值）
 * - file: 处理后的文件（HEIC 会转为 JPEG）
 *
 * 校验项：格式 → 大小 → 文件名长度 → HEIC 转换 → 像素尺寸 → 宽高比
 */
export async function validateImageFile(file) {
  // 1. 格式校验
  const ext = '.' + (file.name || '').split('.').pop().toLowerCase()
  if (!IMAGE_FORMATS.exts.includes(ext)) {
    return { valid: false, error: `不支持的文件格式：${file.name}` }
  }

  // 2. 大小校验
  if (file.size > IMAGE_FORMATS.maxSize) {
    return { valid: false, error: `${file.name} 超过大小限制（${IMAGE_FORMATS.maxSize / 1024 / 1024}MB）` }
  }

  // 3. 文件名长度校验
  if (file.name.length > IMAGE_FORMATS.maxFileNameLength) {
    return { valid: false, error: `文件名称长度不能超过${IMAGE_FORMATS.maxFileNameLength}个字符` }
  }

  // 4. HEIC/HEIF 转 JPEG（浏览器无法解码 HEIC，转后再读元数据）
  if (isHeicFile(file)) {
    try {
      file = await convertHeicToJpegFile(file)
    } catch {
      return { valid: false, error: 'HEIC 文件解码失败，请尝试转换为 JPEG 后再上传' }
    }
  }

  // 5. 读取宽高
  let meta
  try {
    meta = await getImageMetadata(file)
  } catch {
    return { valid: false, error: '无法读取文件信息，请检查文件是否损坏' }
  }

  // 6. 像素 & 宽高比校验（HEIC 等浏览器无法解码时跳过，由后端兜底）
  if (meta.dimensionReadable !== false && meta.width && meta.height) {
    const { width: w, height: h } = meta
    const c = IMAGE_CONSTRAINTS
    const ratio = w / h
    if (w < c.dimMin || w > c.dimMax || h < c.dimMin || h > c.dimMax) {
      return { valid: false, error: `${file.name} 像素需在 ${c.dimMin}-${c.dimMax}px 之间（当前 ${w}×${h}）` }
    }
    if (ratio < c.aspectMin || ratio > c.aspectMax) {
      return { valid: false, error: `${file.name} 宽高比需在 ${c.aspectMin}-${c.aspectMax} 之间（当前 ${ratio.toFixed(2)}）` }
    }
  }

  return { valid: true, file }
}
