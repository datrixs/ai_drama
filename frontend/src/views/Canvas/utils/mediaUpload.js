/**
 * 画布媒体文件统一前端直传工具
 *
 * 把画布节点的图片/视频/音频上传从「后端中转 multipart」改为「前端直传 COS + register-asset」，
 * 避开大文件经后端服务器转存导致的慢速问题。对齐资产中心和画布音频（audioUpload.js）的现有做法。
 *
 * 设计参考 audioUpload.js 的代码风格：前端校验 → 直传 COS → 调 register-asset 注册到节点。
 * 按 itemType 分流：
 * - image：HEIC 先转 JPEG，再校验扩展名/大小，directUploadWithThumbnail 直传原图+缩略图
 * - video：校验扩展名/大小，directUpload 直传，读取 duration（可选）
 * - audio：复用 validateAndUploadAudio（已含校验+直传+duration）
 *
 * 三者最终都调 registerCanvasAsset(itemId, { source:'upload', ... }) 注册到节点。
 */
import { directUpload, directUploadWithThumbnail, isHeicFile, convertHeicToJpegFile } from '@/utils/cosUpload'
import { validateAndUploadAudio } from './audioUpload'
import { registerCanvasAsset } from '@/api/canvas'

// 大小限制（对齐后端 canvas upload-asset 的 validate_upload_and_pick_biz 量级）
export const IMAGE_MAX_BYTES = 20 * 1024 * 1024   // 图片 20MB
export const VIDEO_MAX_BYTES = 100 * 1024 * 1024  // 视频 100MB

// 扩展名白名单
const IMAGE_EXT_WHITELIST = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.heic', '.heif']
const VIDEO_EXT_WHITELIST = ['.mp4', '.webm', '.mov']

/**
 * 从文件名取小写扩展名（含点号），无扩展名返回空串
 * 仿 audioUpload.js 的 getExt
 * @param {string} name
 * @returns {string}
 */
function getExt(name) {
  const idx = (name || '').lastIndexOf('.')
  return idx < 0 ? '' : (name || '').slice(idx).toLowerCase()
}

/**
 * 读取视频时长（秒）
 * 用 video 元素 loadedmetadata 读取，仿 audioUpload.js 的 getAudioDuration
 * 读取失败返回 null（video 不强制 duration，register-asset 可不传）
 * @param {File} file
 * @returns {Promise<number|null>}
 */
function getVideoDuration(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.muted = true
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url)
      const d = video.duration
      if (typeof d !== 'number' || !isFinite(d)) {
        resolve(null)
        return
      }
      resolve(d)
    }
    video.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(null)
    }
    video.src = url
  })
}

/**
 * 画布资产统一前端直传：按 itemType 分流，直传 COS 后调 register-asset 注册到节点。
 *
 * 成功返回 register-asset 的响应（含 item）；失败抛错（调用方 try/catch + ElMessage）。
 * 校验失败（扩展名/大小）抛 Error，HEIC 解码失败抛 Error。
 *
 * @param {string} itemId 节点 id
 * @param {File} file 原始文件
 * @param {'image'|'video'|'audio'} itemType 节点/资产类型
 * @returns {Promise<any>} register-asset 响应（含 item 字段）
 */
export async function uploadCanvasAssetDirect(itemId, file, itemType) {
  if (!file) throw new Error('未选择文件')
  if (!itemId) throw new Error('缺少节点 id')

  if (itemType === 'image') {
    // HEIC/HEIF 先转 JPEG（浏览器无法预览/读尺寸，且后端 register-asset 不接受 heic）
    let imageFile = file
    if (isHeicFile(file)) {
      imageFile = await convertHeicToJpegFile(file)
    }

    // 扩展名校验（HEIC 转码后扩展名已变为 .jpg）
    const ext = getExt(imageFile.name)
    if (!IMAGE_EXT_WHITELIST.includes(ext)) {
      throw new Error(`不支持的图片格式：${file.name}（仅支持 ${IMAGE_EXT_WHITELIST.join(' / ')}）`)
    }
    if (imageFile.size > IMAGE_MAX_BYTES) {
      throw new Error(`图片大小超过限制（${IMAGE_MAX_BYTES / 1024 / 1024}MB）`)
    }

    // 直传原图 + 前端生成缩略图并直传
    const { cos_key, url, thumbnail_url } = await directUploadWithThumbnail(imageFile, {
      category: 'canvas',
      biz: 'image',
    })

    // 注册到节点（source='upload' 会触发后端 sync_to_volc）
    return await registerCanvasAsset(itemId, {
      source: 'upload',
      url,
      cos_key,
      thumbnail_url,
      filename: imageFile.name,
      size: imageFile.size,
      asset_type: 'image',
    })
  }

  if (itemType === 'video') {
    // 扩展名 + 大小校验
    const ext = getExt(file.name)
    if (!VIDEO_EXT_WHITELIST.includes(ext)) {
      throw new Error(`不支持的视频格式：${file.name}（仅支持 ${VIDEO_EXT_WHITELIST.join(' / ')}）`)
    }
    if (file.size > VIDEO_MAX_BYTES) {
      throw new Error(`视频大小超过限制（${VIDEO_MAX_BYTES / 1024 / 1024}MB）`)
    }

    // 直传 COS（保持原始格式）
    const { cos_key, url } = await directUpload(file, {
      category: 'canvas',
      biz: 'video',
      maxSize: VIDEO_MAX_BYTES,
    })

    // 读 duration（可选，失败不阻塞）
    const duration = await getVideoDuration(file)

    return await registerCanvasAsset(itemId, {
      source: 'upload',
      url,
      cos_key,
      filename: file.name,
      size: file.size,
      duration: duration ?? undefined,
      asset_type: 'video',
    })
  }

  if (itemType === 'audio') {
    // 复用 audioUpload：已含扩展名/大小/时长校验 + 直传 COS，返回 { url, cos_key, filename, size, duration }
    const { url, cos_key, filename, size, duration } = await validateAndUploadAudio(file)
    return await registerCanvasAsset(itemId, {
      source: 'upload',
      url,
      cos_key,
      filename,
      size,
      duration,
      asset_type: 'audio',
    })
  }

  throw new Error(`不支持的节点类型：${itemType}`)
}
