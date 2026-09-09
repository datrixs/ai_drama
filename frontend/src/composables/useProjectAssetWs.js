import { ElMessage } from 'element-plus'
import { useProjectAssetStore } from '@/store/project_asset'

/**
 * 处理项目资产库相关的 WebSocket 事件：
 *   - 批量同步（火山 / BytePlus）进度
 *   - 单个资产生成进度
 *   - 自动同步状态回写
 *
 * 注意：project_asset_parse_completed 不在此处处理。该事件需要根据当前是否
 * 处于资产库 Tab 决定是否立即刷新，由各宿主页面自行处理。
 *
 * 复用方：Workspace.vue / EpisodePage.vue / StoryboardEditor.vue
 * 任意挂载了 ProjectAssetLibrary 的页面都应在自己的 WS handleEvent 中调用本函数。
 *
 * @param {string | (() => string)} projectIdOrGet 项目 ID 或返回项目 ID 的函数
 * @returns {(event: any) => Promise<void>} 已包含 project_id 过滤的事件处理函数
 */
export function useProjectAssetWs(projectIdOrGet) {
  const assetStore = useProjectAssetStore()
  const getProjectId = typeof projectIdOrGet === 'function' ? projectIdOrGet : () => projectIdOrGet

  return async function handleProjectAssetEvent(event) {
    const projectId = getProjectId()
    if (event.project_id && event.project_id !== projectId) return

    switch (event.event_type) {
      case 'project_batch_sync_started':
        assetStore.markBatchSyncStarted(event.data?.total || 0, event.data?.asset_ids || [])
        break
      case 'project_batch_sync_progress': {
        const pd = event.data || {}
        if (pd.status === 'success') {
          assetStore.updateVolcSyncStatus(pd.kind, pd.asset_id, pd.volc_id)
        } else {
          const name = pd.asset_name ? `「${pd.asset_name}」` : ''
          ElMessage.error(`${name}同步失败：${pd.error || '未知错误'}`)
        }
        assetStore.setAssetBatchSyncing(pd.asset_id, false)
        assetStore.incBatchSyncDone()
        break
      }
      case 'project_batch_sync_completed':
        ElMessage.success(`批量同步完成：成功 ${event.data?.success_count || 0} 条，失败 ${event.data?.failed_count || 0} 条`)
        assetStore.resetBatchSync()
        assetStore.fetchAssets(projectId)
        break
      case 'project_batch_sync_failed':
        ElMessage.error(`批量同步任务异常：${event.data?.error || '未知错误'}`)
        assetStore.resetBatchSync()
        break
      case 'project_asset_generation_started':
        assetStore.updateAssetStatus(event.data?.asset_type, event.data?.asset_id, 'generating')
        break
      case 'project_asset_generation_completed':
      case 'project_asset_image_modified':
        assetStore.updateAssetImage(
          event.data?.asset_type,
          event.data?.asset_id,
          event.data?.image_url,
          event.data?.thumbnail_url,
        )
        break
      case 'project_asset_generation_failed':
        assetStore.updateAssetStatus(event.data?.asset_type, event.data?.asset_id, 'failed')
        break
      case 'project_asset_volc_sync_completed':
        assetStore.updateVolcSyncStatus(event.data?.asset_type, event.data?.asset_id, event.data?.volc_private_asset_id)
        break
      case 'project_asset_volc_sync_failed':
        assetStore.updateVolcSyncStatus(event.data?.asset_type, event.data?.asset_id, null)
        break
      default:
        break
    }
  }
}
