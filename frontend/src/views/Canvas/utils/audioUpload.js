/**
 * 画布音频节点上传工具
 *
 * 复用短视频页面 EditorBar.vue 的「前端校验 + 直传 COS + register-asset」流程，
 * 提取为独立工具便于画布节点复用。
 *
 * 校验规则（对齐 backend/app/crud/canvas_crud.py 的 AUDIO_MIME_PREFIXES / MAX_AUDIO_BYTES）：
 * - 扩展名：.mp3 / .wav（与短视频页面 ALLOWED_FORMATS.audio 一致）
 * - 大小：≤ 15MB
 * - 时长：≤ 15s（前端 getMediaMetadata 读取，后端二次校验）
 */
import { ElMessage } from 'element-plus'
import { directUpload } from '@/utils/cosUpload'

export const AUDIO_ALLOWED_EXTS = ['.mp3', '.wav']
export const AUDIO_MAX_BYTES = 15 * 1024 * 1024
export const AUDIO_MAX_DURATION_SECONDS = 15

function getExt(name) {
  const idx = (name || '').lastIndexOf('.')
  return idx < 0 ? '' : (name || '').slice(idx).toLowerCase()
}

/**
 * 读取音频元数据（duration）
 * @param {File} file
 * @returns {Promise<number>} duration in seconds（读取失败抛错）
 */
export function getAudioDuration(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const audio = document.createElement('audio')
    audio.preload = 'metadata'
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url)
      const d = audio.duration
      if (typeof d !== 'number' || !isFinite(d)) {
        reject(new Error('无法读取音频时长'))
        return
      }
      resolve(d)
    }
    audio.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('无法读取音频元数据'))
    }
    audio.src = url
  })
}

/**
 * 校验音频文件：扩展名 + 大小 + 时长
 * 失败时弹 ElMessage 并返回 null；成功返回 { file, duration }
 * @param {File} file
 * @returns {Promise<{file: File, duration: number}|null>}
 */
export async function validateAudioFile(file) {
  if (!file) return null
  const ext = getExt(file.name)
  if (!AUDIO_ALLOWED_EXTS.includes(ext)) {
    ElMessage.error(`不支持的音频格式：${file.name}（仅支持 ${AUDIO_ALLOWED_EXTS.join(' / ')}）`)
    return null
  }
  if (file.size > AUDIO_MAX_BYTES) {
    ElMessage.error(`${file.name} 超过大小限制（${AUDIO_MAX_BYTES / 1024 / 1024}MB）`)
    return null
  }
  let duration
  try {
    duration = await getAudioDuration(file)
  } catch (e) {
    ElMessage.error(`${file.name}：${e.message || '无法解析音频'}`)
    return null
  }
  if (duration > AUDIO_MAX_DURATION_SECONDS) {
    ElMessage.error(`${file.name} 时长 ${duration.toFixed(1)}s 超过 ${AUDIO_MAX_DURATION_SECONDS}s 限制`)
    return null
  }
  return { file, duration }
}

/**
 * 校验 + 直传 COS，返回 { url, cos_key, filename, size, duration }
 * 失败时弹 ElMessage 并抛错，调用方 try/catch 即可。
 * @param {File} file
 * @param {string} userId
 * @returns {Promise<{url: string, cos_key: string, filename: string, size: number, duration: number}>}
 */
export async function validateAndUploadAudio(file, userId) {
  const ok = await validateAudioFile(file)
  if (!ok) throw new Error('音频校验未通过')
  const { file: audioFile, duration } = ok
  const { cos_key, url } = await directUpload(audioFile, {
    category: 'canvas',
    biz: 'audio',
    maxSize: AUDIO_MAX_BYTES,
  })
  return {
    url,
    cos_key,
    filename: audioFile.name,
    size: audioFile.size,
    duration,
  }
}
