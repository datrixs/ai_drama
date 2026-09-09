/**
 * WebSocket 事件类型
 */
export const WSEventType = {
  /** 短视频生成进度 */
  SHORT_VIDEO_PROGRESS: 'short_video_progress',
  /** 视频超分任务进度 */
  SUPER_RESOLUTION_PROGRESS: 'super_resolution_progress',
  /** 成片/片段视频生成进度 */
  VIDEO_PROGRESS: 'video_progress',
  /** 剧集分镜生成进度 */
  SCRIPT_PROGRESS: 'script_progress',
  /** 支付订单状态变更 */
  PAY_ORDER_STATUS: 'pay_order_status',
  /** 分集剧本生成进度 */
  EPISODE_SCRIPT_PROGRESS: 'episode_script_progress',
  /** 整集视频合成事件（开始/完成/失败） */
  VIDEO_CONCAT: 'video_concat',
  /** 资产中心-批量同步开始 */
  ASSET_HUB_BATCH_SYNC_STARTED: 'asset_hub_batch_sync_started',
  /** 资产中心-批量同步单条进度 */
  ASSET_HUB_BATCH_SYNC_PROGRESS: 'asset_hub_batch_sync_progress',
  /** 资产中心-批量同步全部完成 */
  ASSET_HUB_BATCH_SYNC_COMPLETED: 'asset_hub_batch_sync_completed',
  /** 资产中心-批量同步任务异常 */
  ASSET_HUB_BATCH_SYNC_FAILED: 'asset_hub_batch_sync_failed',
  /** 项目资产库-批量同步开始 */
  PROJECT_BATCH_SYNC_STARTED: 'project_batch_sync_started',
  /** 项目资产库-批量同步单条进度 */
  PROJECT_BATCH_SYNC_PROGRESS: 'project_batch_sync_progress',
  /** 项目资产库-批量同步全部完成 */
  PROJECT_BATCH_SYNC_COMPLETED: 'project_batch_sync_completed',
  /** 项目资产库-批量同步任务异常 */
  PROJECT_BATCH_SYNC_FAILED: 'project_batch_sync_failed',
  /** 无限画布-节点生成进度（开始/完成/失败） */
  CANVAS_GENERATION_PROGRESS: 'canvas_generation_progress',
}

/**
 * 短视频任务状态
 */
export const ShortVideoStatus = {
  PENDING: 'pending',
  SUBMITTED: 'submitted',
  QUEUED: 'queued',
  PROCESSING: 'processing',
  SUCCEEDED: 'succeeded',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}

/**
 * 视频超分任务状态（语义对齐 ShortVideoStatus，独立导出避免后续语义漂移）
 */
export const SuperResolutionStatus = {
  PENDING: 'pending',
  SUBMITTED: 'submitted',
  PROCESSING: 'processing',
  SUCCEEDED: 'succeeded',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}

/**
 * 视频任务状态（成片/片段）
 */
export const VideoTaskStatus = {
  PENDING: 'pending',
  SUBMITTED: 'submitted',
  PROCESSING: 'video_generating',
  SUCCESS: 'video_completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}

/**
 * 脚本/剧集任务状态
 */
export const ScriptTaskStatus = {
  GENERATING: 'generating',
  COMPLETED: 'completed',
  FAILED: 'failed',
}
