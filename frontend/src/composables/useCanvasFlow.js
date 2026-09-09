import { ref } from 'vue'
import { ElMessage } from 'element-plus'

/**
 * 画布 VueFlow 流图状态管理
 *
 * 维护 flowNodes / flowEdges 与 store 的同步，处理节点拖动防抖、连线创建、
 * 引用上游节点等"流图"层操作。
 */
export function useCanvasFlow({ storeRef, flowNodes, flowEdges, addItem, updateItem, addConnection }) {
  const dragStopTimers = new Map()

  // 允许的连线方向：仅支持 文本→图片→视频
  const ALLOWED_CONNECTION_TARGETS = {
    text: ['image'],
    image: ['video'],
    video: [],
  }

  function getNodeItemType(nodeId) {
    const n = flowNodes.value.find((x) => x.id === nodeId)
    return n?.type || null
  }

  function isConnectionAllowed(connection) {
    const srcType = getNodeItemType(connection.source)
    const tgtType = getNodeItemType(connection.target)
    if (!srcType || !tgtType) return true // 找不到节点不阻拦，交后端校验
    const allowed = ALLOWED_CONNECTION_TARGETS[srcType] || []
    return allowed.includes(tgtType)
  }

  function syncFromStore() {
    const doc = storeRef.value
    if (!doc) return
    // 计算每个 group 的子节点数量（用于标题展示）
    const childCountMap = {}
    for (const it of doc.items || []) {
      if (it.parent_id) {
        childCountMap[it.parent_id] = (childCountMap[it.parent_id] || 0) + 1
      }
    }
    flowNodes.value = (doc.items || []).map((item) => {
      const node = {
        id: item.id,
        type: item.item_type,
        position: { x: item.position_x || 0, y: item.position_y || 0 },
        data: {
          ...item,
          child_count: item.item_type === 'group' ? (childCountMap[item.id] || 0) : undefined,
        },
      }
      if (item.item_type === 'group') {
        node.width = item.width || 240
        node.height = item.height || 120
      }
      if (item.parent_id) {
        node.parentNode = item.parent_id
        node.extent = 'parent'
      }
      return node
    })
    flowEdges.value = (doc.connections || []).map((conn) => ({
      id: conn.id,
      source: conn.source_item_id,
      target: conn.target_item_id,
      sourceHandle: conn.source_handle || 'right',
      targetHandle: conn.target_handle || 'left',
      animated: false,
    }))
  }

  function updateNodeData(itemId, patch, vfUpdateNodeData) {
    const idx = flowNodes.value.findIndex((n) => n.id === itemId)
    if (idx < 0) return
    const next = flowNodes.value.slice()
    next[idx] = {
      ...flowNodes.value[idx],
      data: { ...flowNodes.value[idx].data, ...patch },
    }
    flowNodes.value = next
    if (typeof vfUpdateNodeData === 'function') {
      try {
        vfUpdateNodeData(itemId, (node) => ({ ...node.data, ...patch }))
      } catch (_) {
        // noop
      }
    }
  }

  function onNodeDragStop(event, { commit = true } = {}) {
    const node = event?.node
    if (!node) return
    if (dragStopTimers.has(node.id)) clearTimeout(dragStopTimers.get(node.id))
    dragStopTimers.set(
      node.id,
      setTimeout(async () => {
        dragStopTimers.delete(node.id)
        try {
          await updateItem(node.id, {
            position_x: Math.round(node.position.x),
            position_y: Math.round(node.position.y),
          })
          const item = storeRef.value?.items?.find((i) => i.id === node.id)
          if (item) {
            item.position_x = Math.round(node.position.x)
            item.position_y = Math.round(node.position.y)
          }
        } catch (e) {}
      }, 300)
    )
  }

  function clearDragStopTimers() {
    dragStopTimers.forEach((t) => clearTimeout(t))
    dragStopTimers.clear()
  }

  /**
   * 创建单条连线（内部复用）：前端临时边 + 后端持久化 + 引用写入
   */
  async function createSingleConnection(sourceId, targetId, sourceHandle = 'right', targetHandle = 'left') {
    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    flowEdges.value = [...flowEdges.value, {
      id: tempId,
      source: sourceId,
      target: targetId,
      sourceHandle,
      targetHandle,
      animated: true,
    }]
    try {
      const created = await addConnection({
        source_item_id: sourceId,
        target_item_id: targetId,
        source_handle: sourceHandle,
        target_handle: targetHandle,
      })
      const realId = created?.id
      if (!realId) throw new Error('后端未返回连线 ID')
      flowEdges.value = flowEdges.value.map((e) =>
        e.id === tempId ? { ...e, id: realId, animated: false } : e
      )
      try {
        await addUpstreamReference(sourceId, targetId)
      } catch (_) {
        // 不影响连线本身
      }
    } catch (e) {
      flowEdges.value = flowEdges.value.filter((e) => e.id !== tempId)
      throw e
    }
  }

  async function onConnect(conn) {
    const srcType = getNodeItemType(conn.source)

    // 组节点作为 source：展开为组内每个合法子节点 → target 的单独连线
    if (srcType === 'group') {
      const children = (storeRef.value?.items || []).filter(
        (i) => i.parent_id === conn.source && i.item_type !== 'group',
      )
      if (!children.length) {
        ElMessage.warning('组内没有可连线的子节点')
        return
      }
      let success = 0
      let fail = 0
      for (const child of children) {
        // 检查该子节点类型是否允许连到目标
        const childType = child.item_type
        const allowed = ALLOWED_CONNECTION_TARGETS[childType] || []
        if (!allowed.includes(conn.target ? getNodeItemType(conn.target) : '')) {
          fail++
          continue
        }
        // 去重：已存在连线则跳过
        const exists = flowEdges.value.some(
          (e) => e.source === child.id && e.target === conn.target,
        )
        if (exists) {
          fail++
          continue
        }
        try {
          await createSingleConnection(child.id, conn.target, conn.sourceHandle || 'right', conn.targetHandle || 'left')
          success++
        } catch (_) {
          fail++
        }
      }
      if (success > 0) {
        ElMessage.success(`已为组内 ${success} 个节点创建连线` + (fail > 0 ? `，${fail} 个跳过` : ''))
      } else {
        ElMessage.warning('组内没有可连线的子节点（类型不匹配或连线已存在）')
      }
      return
    }

    // 普通节点连线
    if (!isConnectionAllowed(conn)) {
      const tgtType = getNodeItemType(conn.target)
      ElMessage.warning(`连线方向不允许：${srcType}→${tgtType}（仅支持 文本→图片→视频）`)
      return
    }
    await createSingleConnection(conn.source, conn.target, conn.sourceHandle || 'right', conn.targetHandle || 'left')
  }

  async function addUpstreamReference(sourceId, targetId) {
    if (!sourceId || !targetId || sourceId === targetId) return
    const sourceItem = storeRef.value?.items?.find((i) => i.id === sourceId)
    const targetItem = storeRef.value?.items?.find((i) => i.id === targetId)
    if (!sourceItem || !targetItem) return

    const contentJson = targetItem.content_json || {}
    const tokens = Array.isArray(contentJson.prompt_tokens) ? contentJson.prompt_tokens : []
    if (tokens.some((t) => t.type === 'mention' && t.node_id === sourceId)) return

    const newToken = {
      type: 'mention',
      node_id: sourceId,
      node_type: sourceItem.item_type,
      node_title: sourceItem.title || sourceId,
      role: sourceItem.item_type === 'image' ? 'reference' : null,
    }
    const nextTokens = [...tokens, newToken]
    const plainText = nextTokens.map((t) => {
      if (t.type === 'mention') {
        const role = t.node_type === 'image' && t.role ? `#${t.role}` : ''
        return `[${t.node_title || t.node_id || '节点'}${role}]`
      }
      return t.value || ''
    }).join('')

    try {
      const updated = await updateItem(targetId, {
        content_json: {
          ...contentJson,
          prompt_tokens: nextTokens,
          prompt_plain_text: plainText,
          prompt: plainText,
        },
      })
      return updated
    } catch (e) {
      // 引用写入失败不影响连线本身
    }
  }

  async function deleteSelection() {
    const selectedNodeIds = flowNodes.value.filter((n) => n.selected).map((n) => n.id)
    const selectedEdgeIds = flowEdges.value.filter((e) => e.selected).map((e) => e.id)
    return { selectedNodeIds, selectedEdgeIds }
  }

  return {
    syncFromStore,
    updateNodeData,
    onNodeDragStop,
    clearDragStopTimers,
    onConnect,
    addUpstreamReference,
    isConnectionAllowed,
  }
}
