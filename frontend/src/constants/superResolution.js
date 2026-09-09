/**
 * 视频超分(火山 AI MediaKit 画质增强)前端常量
 *
 * 字段名/类型/value 与火山 API `POST /api/v1/tools/enhance-video` 完全对齐,
 * 详见 docs/super_res.md。
 *
 * 当前 UI 暴露并提交后端的字段:
 *   tool_version / scene / resolution / bitrate_level / fps
 * 后端 schema 中仍保留 resolution_limit(火山 API 支持),仅 UI 不暴露,
 * 历史任务的 resolution_limit 在结果展示时仍会显示。
 * 后端原样透传火山,不做任何字段映射。
 */

// 输入限制
export const SR_INPUT_LIMITS = {
  maxFileSize: 1 * 1024 * 1024 * 1024, // 1GB(本地上传,产品要求)
  maxUrlSize: 10 * 1024 * 1024 * 1024, // 10GB(URL 拉取建议上限,火山文档)
  maxFileNameLength: 64,
  acceptedExts: ['.mp4', '.flv', '.ts', '.avi', '.mov', '.wmv', '.mkv'],
  acceptedMimes: 'video/mp4,video/x-flv,video/mp2t,video/x-msvideo,video/quicktime,video/x-ms-wmv,video/x-matroska',
}

/**
 * 场景预设(对应火山 scene 字段)
 *
 * 注意:
 * - 每个预设带一组 defaults,切换时自动套用,用户可继续微调
 * - 没有"自定义"预设(火山此 API 不暴露算子,custom 失去意义)
 *
 * value 与火山 scene 取值完全一致: common/ugc/short_series/aigc/old_film
 *
 * 关于 scene 与 tool_version 的关系:
 * - 火山文档明确 scene 仅在 tool_version=standard 时生效
 * - 产品决策:UI 不做联动禁用,选 professional 时场景预设仍可点击,
 *   后端原样透传,火山自行忽略该字段
 */
export const SR_SCENES = [
  {
    value: 'common',
    label: '通用',
    desc: '效果均衡,适合大多数视频',
    icon: 'general',
    defaults: {
      tool_version: 'standard',
      resolution: null,
      bitrate_level: 'medium',
      fps: null,
    },
  },
  {
    value: 'ugc',
    label: 'UGC 短视频',
    desc: '修复压缩失真、模糊、块效应',
    icon: 'ugc',
    defaults: {
      tool_version: 'standard',
      resolution: null,
      bitrate_level: 'medium',
      fps: null,
    },
  },
  {
    value: 'short_series',
    label: '短剧',
    desc: '人像增强,提升视觉表现力',
    icon: 'drama',
    defaults: {
      tool_version: 'professional',
      resolution: null,
      bitrate_level: 'high',
      fps: null,
    },
  },
  {
    value: 'aigc',
    label: 'AIGC 内容',
    desc: '针对 AI 生成低清视频超分重绘',
    icon: 'aigc',
    defaults: {
      tool_version: 'professional',
      resolution: null,
      bitrate_level: 'high',
      fps: null,
    },
  },
  {
    value: 'old_film',
    label: '老片修复',
    desc: '低分辨率、卡顿、色彩失真、噪点',
    icon: 'old_film',
    defaults: {
      tool_version: 'professional',
      resolution: null,
      bitrate_level: 'high',
      fps: 60,
    },
  },
]

/**
 * 工具版本(对应火山 tool_version 字段)
 * standard=标准版(平衡速度与画质);professional=专业版(镜头级画质增强)
 */
export const SR_TOOL_VERSIONS = [
  { value: 'standard', label: '标准版', desc: '兼顾速度与画质' },
  { value: 'professional', label: '专业版', desc: '镜头级画质增强' },
]

/**
 * 目标分辨率(对应火山 resolution 字段)
 * null=不传(保持原片分辨率,即"与源一致")
 *
 * 注:已移除 240p/360p/480p/540p 档位(超分场景下向下采样无意义)。
 * "与源一致"=不下发 resolution,火山按原片分辨率输出。
 */
export const SR_RESOLUTIONS = [
  { value: null, label: '与源一致' },
  { value: '720p', label: '720p' },
  { value: '1080p', label: '1080p' },
  { value: '2k', label: '2K' },
  { value: '4k', label: '4K' },
]

/**
 * 帧率(对应火山 fps 字段)
 * null=不传(保持原片帧率,即"与源一致")
 * 取值范围 [15, 120]
 */
export const SR_FPS_OPTIONS = [
  { value: null, label: '与源一致' },
  { value: 24, label: '24 fps' },
  { value: 25, label: '25 fps' },
  { value: 30, label: '30 fps' },
  { value: 50, label: '50 fps' },
  { value: 60, label: '60 fps' },
  { value: 120, label: '120 fps' },
]

export const SR_FPS_RANGE = { min: 15, max: 120 }

/**
 * 码率(对应火山 bitrate_level 字段)
 * 产品默认选中 medium(中码率-推荐)
 */
export const SR_BITRATE_LEVELS = [
  { value: 'low', label: '低码率' },
  { value: 'medium', label: '中码率(推荐)' },
  { value: 'high', label: '高码率' },
]
