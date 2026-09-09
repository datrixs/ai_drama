/**
 * COS 直传工具函数
 * 前端通过预签名 PUT URL 直传文件到腾讯 COS，不经过后端服务器
 */
import request from '@/utils/request'

/**
 * 从文件名或 MIME 类型推断扩展名
 * @param {File} file
 * @returns {string}
 */
function inferExtension(file) {
  if (file.name && file.name.includes('.')) {
    return file.name.split('.').pop().toLowerCase()
  }
  const mimeMap = {
    // Image
    'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp',
    'image/gif': 'gif', 'image/bmp': 'bmp', 'image/svg+xml': 'svg',
    // Video
    'video/mp4': 'mp4', 'video/webm': 'webm', 'video/quicktime': 'mov',
    'video/x-msvideo': 'avi', 'video/avi': 'avi',
    'video/x-matroska': 'mkv', 'video/x-flv': 'flv',
    'video/mpeg': 'mpeg', 'video/3gpp': '3gp',
    // Audio
    'audio/mpeg': 'mp3', 'audio/mp3': 'mp3', 'audio/wav': 'wav',
    'audio/ogg': 'ogg', 'audio/m4a': 'm4a', 'audio/flac': 'flac',
    'audio/aac': 'aac',
  }
  return mimeMap[file.type] || 'bin'
}

/**
 * 调用后端获取直传凭证
 * @param {Object} params - { category, biz, file_extension, content_type }
 * @returns {Promise<{ upload_url: string, cos_key: string, url: string, expires_in: number }>}
 */
export async function getUploadCredential(params) {
  const res = await request.post('/asset-hub/upload-credential', params)
  // axios 拦截器已解包 response.data.data，res 直接就是 { upload_url, cos_key, url, expires_in }
  return res
}

/**
 * 直传文件到 COS（保持原始格式）
 * @param {File} file - 原始文件
 * @param {Object} options - { category, biz, maxSize }
 * @returns {Promise<{ cos_key: string, url: string }>}
 */
export async function directUpload(file, options = {}) {
  const { category = 'upload', biz = 'image', maxSize = null } = options

  if (maxSize && file.size > maxSize) {
    throw new Error(`文件大小超过限制（${(maxSize / 1024 / 1024).toFixed(0)}MB）`)
  }

  const ext = inferExtension(file)
  const contentType = file.type || 'application/octet-stream'

  // 1. 获取预签名上传凭证
  const credential = await getUploadCredential({
    category,
    biz,
    file_extension: ext,
    content_type: contentType,
  })

  // 2. PUT 直传到 COS
  const response = await fetch(credential.upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: file,
  })

  if (!response.ok) {
    throw new Error(`COS 上传失败: ${response.status} ${response.statusText}`)
  }

  return {
    cos_key: credential.cos_key,
    url: credential.url,
  }
}

/**
 * 判断是否 HEIC/HEIF 文件（Chrome/Firefox 无法原生预览，需前端解码）
 * @param {File} file
 * @returns {boolean}
 */
export function isHeicFile(file) {
  const name = (file?.name || '').toLowerCase()
  return name.endsWith('.heic') || name.endsWith('.heif')
}

// 动态加载 heic2any（~1.5MB），仅首次遇到 HEIC 时下载
let _heic2anyLoader = null
function loadHeic2any() {
  if (!_heic2anyLoader) {
    _heic2anyLoader = import('heic2any').then(m => m.default || m)
  }
  return _heic2anyLoader
}

/**
 * 将 HEIC/HEIF 文件转换为 JPEG File（保留原文件名，扩展名替换为 .jpg）
 * 转换质量 0.92，火山支持 JPEG 输入，无需保留 HEIC 原始格式
 * @param {File} file
 * @returns {Promise<File>} JPEG File
 */
export async function convertHeicToJpegFile(file) {
  const heic2any = await loadHeic2any()
  const blob = await heic2any({ blob: file, toType: 'image/jpeg', quality: 0.92 })
  const jpegBlob = Array.isArray(blob) ? blob[0] : blob
  const newName = file.name.replace(/\.(heic|heif)$/i, '.jpg')
  return new File([jpegBlob], newName, { type: 'image/jpeg', lastModified: file.lastModified })
}

/**
 * 用 Canvas 在浏览器中生成缩略图 Blob（按比例缩放，最长边 320，JPEG quality 80）
 * 与后端 backend/app/utils/thumbnail.py 的 THUMB_MAX_SIZE=(320,320) / QUALITY=80 保持一致
 * @param {File|Blob} file - 原始图片
 * @param {Object} options - { maxSize: 320, quality: 0.8 }
 * @returns {Promise<Blob|null>} 缩略图 Blob；图片解码失败时返回 null
 */
export async function generateThumbnailBlob(file, options = {}) {
  const { maxSize = 320, quality = 0.8 } = options
  if (!file || !file.type || !file.type.startsWith('image/')) return null

  const bitmap = await loadImageBitmap(file).catch(() => null)
  if (!bitmap) return null

  // 按比例缩放：保持宽高比，最长边不超过 maxSize
  const ratio = Math.min(maxSize / bitmap.width, maxSize / bitmap.height, 1)
  const w = Math.max(1, Math.round(bitmap.width * ratio))
  const h = Math.max(1, Math.round(bitmap.height * ratio))

  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.drawImage(bitmap, 0, 0, w, h)

  if (bitmap.close) bitmap.close()

  return await new Promise((resolve) => {
    canvas.toBlob(
      (blob) => resolve(blob),
      'image/jpeg',
      quality,
    )
  })
}

async function loadImageBitmap(file) {
  if ('createImageBitmap' in window) {
    return await createImageBitmap(file)
  }
  const url = URL.createObjectURL(file)
  try {
    return await new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = reject
      img.src = url
    })
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

/**
 * 直传图片到 COS，同时在前端生成缩略图并直传。返回原图 + 缩略图两个 cos_key。
 * 用于带宽有限场景：避免后端从 COS 回拉原图再生成缩略图。
 * @param {File} file - 原始图片
 * @param {Object} options - { category, biz, maxSize }
 * @returns {Promise<{ cos_key: string, url: string, thumbnail_cos_key: string|null, thumbnail_url: string|null }>}
 */
export async function directUploadWithThumbnail(file, options = {}) {
  const { category = 'upload', biz = 'image' } = options

  // 并行：原图凭证 + 缩略图生成
  const ext = inferExtension(file)
  const contentType = file.type || 'application/octet-stream'
  const [originalCredential, thumbBlob] = await Promise.all([
    getUploadCredential({ category, biz, file_extension: ext, content_type: contentType }),
    generateThumbnailBlob(file),
  ])

  // 上传原图
  const uploads = [
    fetch(originalCredential.upload_url, {
      method: 'PUT',
      headers: { 'Content-Type': contentType },
      body: file,
    }),
  ]

  let thumbCredential = null
  if (thumbBlob) {
    thumbCredential = await getUploadCredential({
      category: 'upload',
      biz: `${biz}-thumb`,
      file_extension: 'jpg',
      content_type: 'image/jpeg',
    })
    uploads.push(
      fetch(thumbCredential.upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': 'image/jpeg' },
        body: thumbBlob,
      }),
    )
  }

  const responses = await Promise.all(uploads)
  for (const r of responses) {
    if (!r.ok) {
      throw new Error(`COS 上传失败: ${r.status} ${r.statusText}`)
    }
  }

  return {
    cos_key: originalCredential.cos_key,
    url: originalCredential.url,
    thumbnail_cos_key: thumbCredential ? thumbCredential.cos_key : null,
    thumbnail_url: thumbCredential ? thumbCredential.url : null,
  }
}
