import request from '@/utils/request'

export function getProjectAssets(projectId) {
  return request.get(`/projects/${projectId}/storyboard-assets`)
}

export function syncAssetToVolc(projectId, assetId, assetKind) {
  return request.post(`/volc/projects/${projectId}/sync-asset`, {
    asset_id: assetId,
    asset_kind: assetKind,
  })
}
