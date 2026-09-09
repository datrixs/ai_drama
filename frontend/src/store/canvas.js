import { ref } from 'vue'
import {
  listCanvasDocuments, createCanvasDocument, getCanvasDocument,
  updateCanvasDocument, deleteCanvasDocument,
  createCanvasItem, updateCanvasItem, deleteCanvasItem,
  batchUpdateCanvasItems,
  createCanvasConnection, deleteCanvasConnection,
  listCanvasGenerations, applyCanvasGeneration,
  registerCanvasAsset,
  syncCanvasItemVolcano,
  saveCanvasItemToAssetCenter,
  batchSaveCanvasItemsToAssetCenter,
} from '@/api/canvas'

const documents = ref([])
const currentDocument = ref(null)
const loading = ref(false)

export function useCanvasStore() {
  async function fetchDocuments() {
    loading.value = true
    try {
      documents.value = await listCanvasDocuments()
    } finally {
      loading.value = false
    }
  }

  async function createDocument(title) {
    const doc = await createCanvasDocument({ title: title || '未命名画布' })
    documents.value.unshift(doc)
    return doc
  }

  async function openDocument(documentId) {
    loading.value = true
    try {
      currentDocument.value = await getCanvasDocument(documentId)
      return currentDocument.value
    } finally {
      loading.value = false
    }
  }

  async function renameDocument(documentId, title) {
    const updated = await updateCanvasDocument(documentId, { title })
    const idx = documents.value.findIndex((d) => d.id === documentId)
    if (idx >= 0) documents.value[idx] = { ...documents.value[idx], ...updated }
    if (currentDocument.value?.id === documentId) {
      currentDocument.value = { ...currentDocument.value, ...updated }
    }
    return updated
  }

  async function removeDocument(documentId) {
    await deleteCanvasDocument(documentId)
    documents.value = documents.value.filter((d) => d.id !== documentId)
    if (currentDocument.value?.id === documentId) {
      currentDocument.value = null
    }
  }

  async function addItem(item) {
    const newItem = await createCanvasItem(currentDocument.value.id, item)
    currentDocument.value.items.push(newItem)
    return newItem
  }

  async function updateItem(itemId, patch) {
    const updated = await updateCanvasItem(itemId, patch)
    const idx = currentDocument.value.items.findIndex((i) => i.id === itemId)
    if (idx >= 0) {
      // 文本/标题/配置保存时，后端返回的 last_output_json / cover_url 是重新签名的媒体
      // URL（预签名每次字符串都不同）。若整体回写，会让编辑浮层（outputUrl）与画布节点
      // 的图片/视频 src 改变 → 媒体重新加载 → 闪烁抖动。
      // 媒体输出只由 applyGeneration / registerAsset / syncItemVolcano 等独立流程维护，
      // updateItem 不负责媒体，故显式剔除这两个字段，保留本地已有媒体引用不变。
      const { last_output_json: _o, cover_url: _c, ...safeUpdated } = updated || {}
      currentDocument.value.items[idx] = { ...currentDocument.value.items[idx], ...safeUpdated }
    }
    return updated
  }

  async function removeItem(itemId) {
    await deleteCanvasItem(itemId)
    // 若删除的是 group 节点：后端会自动 detach 子节点（parent_id 置空），
    // 前端 store.items 也需同步清理，避免下次 syncFromStore 把子节点挂回已删的 group
    currentDocument.value.items = currentDocument.value.items
      .map((it) => (it.parent_id === itemId ? { ...it, parent_id: null } : it))
      .filter((i) => i.id !== itemId)
    currentDocument.value.connections = currentDocument.value.connections.filter(
      (c) => c.source_item_id !== itemId && c.target_item_id !== itemId
    )
  }

  async function batchUpdateItems(documentId, updates) {
    return await batchUpdateCanvasItems(documentId, updates)
  }

  function patchItemsLocally(patchesById) {
    if (!currentDocument.value?.items) return
    currentDocument.value.items = currentDocument.value.items.map((it) => {
      const p = patchesById[it.id]
      if (!p) return it
      return { ...it, ...p }
    })
  }

  async function addConnection(conn) {
    const newConn = await createCanvasConnection(currentDocument.value.id, conn)
    currentDocument.value.connections.push(newConn)
    return newConn
  }

  async function removeConnection(connId) {
    await deleteCanvasConnection(connId)
    currentDocument.value.connections = currentDocument.value.connections.filter((c) => c.id !== connId)
  }

  function resetCurrent() {
    currentDocument.value = null
  }

  async function fetchGenerations(itemId, params = {}) {
    return listCanvasGenerations(itemId, params)
  }

  async function applyGeneration(itemId, generationId) {
    const updated = await applyCanvasGeneration(itemId, generationId)
    const idx = currentDocument.value.items.findIndex((i) => i.id === itemId)
    if (idx >= 0) {
      currentDocument.value.items[idx] = { ...currentDocument.value.items[idx], ...updated }
    }
    return updated
  }

  async function registerAsset(itemId, payload) {
    const resp = await registerCanvasAsset(itemId, payload)
    const updated = resp?.item || resp
    if (updated?.id) {
      const idx = currentDocument.value.items.findIndex((i) => i.id === itemId)
      if (idx >= 0) {
        currentDocument.value.items[idx] = { ...currentDocument.value.items[idx], ...updated }
      }
    }
    return resp
  }

  async function syncItemVolcano(itemId) {
    const resp = await syncCanvasItemVolcano(itemId)
    const updated = resp?.item || resp
    if (updated?.id) {
      const idx = currentDocument.value.items.findIndex((i) => i.id === itemId)
      if (idx >= 0) {
        currentDocument.value.items[idx] = { ...currentDocument.value.items[idx], ...updated }
      }
    }
    return resp
  }

  async function saveItemToAssetCenter(itemId, payload) {
    return await saveCanvasItemToAssetCenter(itemId, payload)
  }

  async function batchSaveToAssetCenter(documentId, payload) {
    return await batchSaveCanvasItemsToAssetCenter(documentId, payload)
  }

  return {
    documents,
    currentDocument,
    loading,
    fetchDocuments,
    createDocument,
    openDocument,
    renameDocument,
    removeDocument,
    addItem,
    updateItem,
    removeItem,
    batchUpdateItems,
    patchItemsLocally,
    addConnection,
    removeConnection,
    resetCurrent,
    fetchGenerations,
    applyGeneration,
    registerAsset,
    syncItemVolcano,
    saveItemToAssetCenter,
    batchSaveToAssetCenter,
  }
}
