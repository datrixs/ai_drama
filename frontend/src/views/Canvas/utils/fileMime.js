/**
 * 画布拖入文件的 MIME / 扩展名判定
 * 用于：拖本地文件到画布时按文件类型决定节点类型（text/image/video）
 */

const IMAGE_EXT = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'svg']
const VIDEO_EXT = ['mp4', 'webm', 'mov', 'avi', 'mkv', 'flv', 'mpeg', '3gp']
const AUDIO_EXT = ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'weba', 'webm']
const TEXT_EXT = ['txt', 'md']

function getExt(file) {
  const name = file?.name || ''
  const idx = name.lastIndexOf('.')
  if (idx < 0) return ''
  return name.slice(idx + 1).toLowerCase()
}

export function isImageFile(file) {
  if (!file) return false
  if (file.type && /^image\/(jpeg|png|webp|gif|bmp|svg\+xml)$/i.test(file.type)) return true
  return IMAGE_EXT.includes(getExt(file))
}

export function isVideoFile(file) {
  if (!file) return false
  if (file.type && /^video\/(mp4|webm|quicktime|x-msvideo|x-matroska|x-flv|mpeg|3gpp)$/i.test(file.type)) return true
  return VIDEO_EXT.includes(getExt(file))
}

export function isAudioFile(file) {
  if (!file) return false
  if (file.type && /^audio\/(mpeg|mp3|wav|wave|x-wav|m4a|x-m4a|aac|ogg|flac|x-flac|webm)$/i.test(file.type)) return true
  return AUDIO_EXT.includes(getExt(file))
}

export function isTextFile(file) {
  if (!file) return false
  if (file.type === 'text/plain' || file.type === 'text/markdown') return true
  return TEXT_EXT.includes(getExt(file))
}

/**
 * 按文件类型推断画布节点类型
 * @returns {'text'|'image'|'video'|'audio'|null}
 */
export function pickNodeTypeForFile(file) {
  if (!file) return null
  if (isImageFile(file)) return 'image'
  if (isVideoFile(file)) return 'video'
  if (isAudioFile(file)) return 'audio'
  if (isTextFile(file)) return 'text'
  return null
}
