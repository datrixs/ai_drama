import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadCanvasAssetDirect } from '@/views/Canvas/utils/mediaUpload'
import { pickNodeTypeForFile } from '@/views/Canvas/utils/fileMime'

/**
 * 画布拖拽文件落点计算 + 文本/图片/视频分发
 *
 * @param {object} opts
 * @param {import('vue').Ref<any[]>} opts.flowNodes
 * @param {(id: string) => any} opts.findNode
 * @param {(point: {x: number, y: number}) => {x: number, y: number}} opts.screenToFlowCoordinate
 * @param {(item: any) => Promise<any>} opts.addItem
 * @param {(id: string, patch: any) => Promise<any>} opts.updateItem
 * @param {(item: {id: string}) => void} opts.onAssetImported - 资产导入成功后回调（把最新 item 字段 patch 回节点）
 */
export function useCanvasDragDrop({ flowNodes, findNode, screenToFlowCoordinate, addItem, updateItem, onAssetImported }) {
  const dragActive = ref(false)

  function onCanvasDragOver(e) {
    if (e.dataTransfer?.types?.includes('Files')) {
      dragActive.value = true
    }
  }

  function onCanvasDragLeave(e) {
    if (e.relatedTarget && e.currentTarget.contains(e.relatedTarget)) return
    dragActive.value = false
  }

  async function onCanvasDrop(e, { creatingItem }) {
    dragActive.value = false
    const files = Array.from(e.dataTransfer?.files || [])
    if (files.length === 0) return

    let hitNodeId = null
    const hitEl = document.elementFromPoint(e.clientX, e.clientY)
    const hitNodeWrap = hitEl?.closest('[data-id]')
    if (hitNodeWrap) {
      const id = hitNodeWrap.getAttribute('data-id')
      const node = findNode(id)
      if (node) hitNodeId = id
    }

    const dropPos = screenToFlowCoordinate({ x: e.clientX, y: e.clientY })

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const nodeType = pickNodeTypeForFile(file)
      if (!nodeType) {
        ElMessage.warning(`不支持的文件类型：${file.name}`)
        continue
      }
      const offsetPos = { x: dropPos.x + i * 30, y: dropPos.y + i * 30 }
      await processDroppedFile(file, nodeType, hitNodeId, offsetPos, { creatingItem })
    }
  }

  async function processDroppedFile(file, nodeType, hitNodeId, dropPos, { creatingItem }) {
    if (nodeType === 'text') {
      let targetItemId = hitNodeId
      if (!targetItemId) {
        const created = await createItemWithPosition('text', dropPos, { creatingItem })
        if (!created) return
        targetItemId = created.id
      } else {
        const node = findNode(targetItemId)
        if (node?.data?.item_type !== 'text') {
          ElMessage.warning('文本文件只能拖到文本节点')
          return
        }
      }
      try {
        const text = await readFileAsText(file)
        const item = flowNodes.value.find((n) => n.id === targetItemId)
        const contentJson = { ...(item?.data?.content_json || {}), body: text }
        await updateItem(targetItemId, { content_json: contentJson })
        onAssetImported?.({ id: targetItemId, content_json: contentJson })
        ElMessage.success(`已导入 ${file.name}`)
      } catch (err) {
        ElMessage.error(err?.message || '文本导入失败')
      }
      return
    }

    let targetItemId = hitNodeId
    if (targetItemId) {
      const node = findNode(targetItemId)
      if (node?.data?.item_type !== nodeType) {
        ElMessage.warning(`${nodeType === 'image' ? '图片' : '视频'}文件只能拖到同类节点`)
        return
      }
    } else {
      const created = await createItemWithPosition(nodeType, dropPos, { creatingItem })
      if (!created) return
      targetItemId = created.id
    }

    try {
      const resp = await uploadCanvasAssetDirect(targetItemId, file, nodeType)
      const updated = resp?.item
      if (updated) onAssetImported?.(updated)
      ElMessage.success(nodeType === 'image' ? '图片已导入' : '视频已导入')
    } catch (err) {
      ElMessage.error(err?.message || '文件导入失败')
    }
  }

  async function createItemWithPosition(itemType, pos, { creatingItem }) {
    creatingItem.value = true
    try {
      const created = await addItem({
        item_type: itemType,
        title: '',
        position_x: Math.round(pos.x),
        position_y: Math.round(pos.y),
        width: 240,
        height: 120,
      })
      flowNodes.value.push({
        id: created.id,
        type: created.item_type,
        position: { x: created.position_x, y: created.position_y },
        data: { ...created },
      })
      return created
    } catch (e) {
      return null
    } finally {
      creatingItem.value = false
    }
  }

  function readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || ''))
      reader.onerror = () => reject(new Error('读取文件失败'))
      reader.readAsText(file)
    })
  }

  return {
    dragActive,
    onCanvasDragOver,
    onCanvasDragLeave,
    onCanvasDrop,
  }
}
