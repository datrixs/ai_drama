import { ElMessage } from 'element-plus'

/**
 * 画布组合节点（group node）打组/解组逻辑
 *
 * Vue Flow 通过 Node.parentNode + extent:'parent' 形成父子层级：
 * - 子节点 position 自动相对父节点渲染
 * - 拖动父节点时子节点视觉跟随，无需手动改子节点坐标
 * - removeNodes(parentId) 默认级联删子节点，解组前必须先清空 parentNode
 *
 * 后端通过 canvas_item.parent_id 持久化（仅单层，group 节点不能再被打组）。
 *
 * 实现要点：直接整体替换 flowNodes.value（v-model:nodes 双向绑定），
 * 不使用 Vue Flow 命令式 API（addNodes/updateNode），避免异步注册导致的时序问题。
 *
 * @param {object} opts
 * @param {import('vue').Ref<object>} opts.storeRef - useCanvasStore 返回的 currentDocument
 * @param {import('vue').Ref<any[]>} opts.flowNodes
 * @param {() => any[]} opts.getSelectedNodes
 * @param {(payload: any) => Promise<any>} opts.addItem - store.addItem
 * @param {(id: string) => Promise<any>} opts.removeItem - store.removeItem
 * @param {(documentId: string, updates: any[]) => Promise<any>} opts.batchUpdateItems - store.batchUpdateItems
 * @param {(patchesById: Record<string, any>) => void} opts.patchItemsLocally
 * @param {() => void} opts.onMutation
 */
export function useCanvasGrouping({
  storeRef,
  flowNodes,
  getSelectedNodes,
  addItem,
  removeItem,
  batchUpdateItems,
  patchItemsLocally,
  onMutation,
  findNode,
  removeFlowNodes,
  updateFlowNode,
}) {
  const PADDING = 24

  function canGroup() {
    const sel = (getSelectedNodes?.() || flowNodes.value.filter((n) => n.selected)).filter(
      (n) => n.type !== 'group' && !n.parentNode,
    )
    return sel.length >= 2
  }

  /**
   * 计算节点绝对坐标。
   * 必须从 VueFlow 内部状态读 computedPosition —— v-model 数组里的 computedPosition
   * 可能是过时的或缺失（v-model 双向绑定的回写存在时序/缺字段问题）。
   * 顶层节点 position 即绝对坐标。
   */
  function getAbsolutePos(n) {
    const internal = findNode?.(n.id)
    const cp = internal?.computedPosition
    if (cp && typeof cp.x === 'number' && typeof cp.y === 'number') {
      return { x: cp.x, y: cp.y }
    }
    if (typeof n.computedPosition?.x === 'number') return { x: n.computedPosition.x, y: n.computedPosition.y }
    return { x: n.position?.x ?? 0, y: n.position?.y ?? 0 }
  }

  function getNodeSize(n) {
    return {
      w: n.width || n.dimensions?.width || 240,
      h: n.height || n.dimensions?.height || 120,
    }
  }

  /**
   * 把当前选中的节点（非 group、非子节点）打组。
   * 关键：通过整体替换 flowNodes.value 实现原子更新，避免 Vue Flow 异步 API 时序问题。
   */
  async function groupSelected() {
    const doc = storeRef.value
    if (!doc) return null
    const selected = (getSelectedNodes?.() || flowNodes.value.filter((n) => n.selected)).filter(
      (n) => n.type !== 'group' && !n.parentNode,
    )
    if (selected.length < 2) {
      ElMessage.warning('请至少选择 2 个节点再打组')
      return null
    }

    // 包围盒（绝对坐标）
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    for (const n of selected) {
      const { x, y } = getAbsolutePos(n)
      const { w, h } = getNodeSize(n)
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x + w)
      maxY = Math.max(maxY, y + h)
    }
    const groupX = Math.round(minX - PADDING)
    const groupY = Math.round(minY - PADDING)
    const groupW = Math.round(maxX - minX + PADDING * 2)
    const groupH = Math.round(maxY - minY + PADDING * 2)

    // 后端先建组节点（拿到持久化 id）
    let groupItem
    try {
      groupItem = await addItem({
        item_type: 'group',
        title: `组合 · ${selected.length} 个节点`,
        position_x: groupX,
        position_y: groupY,
        width: groupW,
        height: groupH,
        parent_id: null,
      })
    } catch (e) {
      ElMessage.error('打组失败：' + (e?.message || '未知错误'))
      return null
    }
    const groupId = groupItem.id

    // 整体替换 flowNodes：插入 group + 改写子节点（parentNode/extent/相对坐标）
    const selectedIdSet = new Set(selected.map((n) => n.id))
    const nextNodes = []
    const updates = []
    for (const n of flowNodes.value) {
      if (n.id === groupId) {
        // 防御性：理论上不会出现
        nextNodes.push(n)
        continue
      }
      if (selectedIdSet.has(n.id)) {
        const abs = getAbsolutePos(n)
        const relX = Math.round(abs.x - groupX)
        const relY = Math.round(abs.y - groupY)
        const child = {
          ...n,
          parentNode: groupId,
          extent: 'parent',
          position: { x: relX, y: relY },
          // 触发 Vue Flow 把节点视为"已挂载到父节点"：清掉缓存过的绝对位置
          computedPosition: undefined,
        }
        nextNodes.push(child)
        updates.push({
          id: n.id,
          position_x: relX,
          position_y: relY,
          parent_id: groupId,
        })
      } else {
        nextNodes.push(n)
      }
    }
    // group 节点插入到数组开头，确保 Vue Flow 先注册父节点（子节点的 parentNode 才能解析）
    const groupNode = {
      id: groupId,
      type: 'group',
      position: { x: groupX, y: groupY },
      width: groupW,
      height: groupH,
      data: { ...groupItem, child_count: selected.length },
      selectable: true,
    }
    flowNodes.value = [groupNode, ...nextNodes]

    try {
      await batchUpdateItems(doc.id, updates)
      const patchesById = { [groupId]: { position_x: groupX, position_y: groupY } }
      for (const u of updates) {
        patchesById[u.id] = {
          parent_id: u.parent_id,
          position_x: u.position_x,
          position_y: u.position_y,
        }
      }
      patchItemsLocally?.(patchesById)
    } catch (e) {
      ElMessage.warning('组合关系暂未保存，请重试或刷新页面')
    }

    onMutation?.()
    ElMessage.success(`已打组 ${selected.length} 个节点`)
    return { groupId, childIds: selected.map((n) => n.id) }
  }

  /**
   * 解组：先快照子节点绝对坐标 → 后端删 group + 批量更新子节点位置 →
   * 通过 VueFlow 命令式 API（removeNodes + updateNode）直接改内部 state.nodes。
   *
   * 为什么不用 flowNodes.value 整体替换？
   *   v-model watch（pauseModel/pauseStore）在 await 之后某些时序下不会触发，
   *   导致 group 视觉残留、子节点 parentNode 不清。VueFlow 的 API 路径走
   *   nodesChange → applyNodeChanges → 直接 splice state.nodes，同步可靠。
   *
   * 为什么不用 forceRebuildFlow（:key 重建）？
   *   会卸载整个 <VueFlow>，所有节点 DOM 销毁重建 —— 正在编辑的 input/textarea
   *   立刻失焦。打组/解组是高频操作，副作用太重。
   */
  async function ungroupNode(groupId) {
    const doc = storeRef.value
    if (!doc || !groupId) return

    // 1. 快照子节点 + VueFlow 内部绝对坐标（必须在任何变更前读）
    const childNodes = flowNodes.value.filter((n) => n.parentNode === groupId)
    const childrenSnapshot = childNodes.map((n) => {
      const abs = getAbsolutePos(n)
      return {
        id: n.id,
        absX: Math.round(abs.x),
        absY: Math.round(abs.y),
      }
    })
    const parent = flowNodes.value.find((n) => n.id === groupId)

    // 2. 后端：删 group（cascade 子节点 parent_id），再批量更新子节点绝对坐标
    const updates = childrenSnapshot.map((c) => ({
      id: c.id,
      position_x: c.absX,
      position_y: c.absY,
      parent_id: '',
    }))

    try {
      await removeItem(groupId)
    } catch (e) {
      ElMessage.error('解组失败：' + (e?.message || '未知错误'))
      return
    }

    if (updates.length) {
      try {
        await batchUpdateItems(doc.id, updates)
        const patchesById = {}
        for (const u of updates) {
          patchesById[u.id] = {
            parent_id: null,
            position_x: u.position_x,
            position_y: u.position_y,
          }
        }
        patchItemsLocally?.(patchesById)
      } catch (e) {
        ElMessage.warning('子节点位置暂未保存，请重试或刷新页面')
      }
    }

    // 3. VueFlow API 路径：移除 group（removeChildren=false，保留子节点），
    //    再 updateNode 清子节点的 parentNode + 写绝对坐标。
    //    API 直接改 state.nodes，绕开 v-model watch 时序。
    if (typeof removeFlowNodes === 'function') {
      try { removeFlowNodes([groupId], false, false) } catch (_) {}
    }
    if (typeof updateFlowNode === 'function') {
      for (const c of childrenSnapshot) {
        try {
          // 默认 replace:false → Object.assign(node, nextNode)
          // 显式写 parentNode: undefined 才能覆盖旧 groupId（Object.assign 会复制 undefined）
          updateFlowNode(c.id, {
            parentNode: undefined,
            extent: undefined,
            position: { x: c.absX, y: c.absY },
            computedPosition: undefined,
          })
        } catch (_) {}
      }
    } else {
      // 兜底：API 不可用时直接改 flowNodes（旧逻辑，不可靠但聊胜于无）
      const childIdSet = new Set(childrenSnapshot.map((c) => c.id))
      const absMap = new Map(childrenSnapshot.map((c) => [c.id, c]))
      flowNodes.value = flowNodes.value
        .filter((n) => n.id !== groupId)
        .map((n) => {
          if (!childIdSet.has(n.id)) return n
          const abs = absMap.get(n.id)
          return {
            ...n,
            parentNode: undefined,
            extent: undefined,
            position: { x: abs.absX, y: abs.absY },
            computedPosition: undefined,
          }
        })
    }

    onMutation?.()

    ElMessage.success(`已解组${parent ? '（' + childrenSnapshot.length + ' 个节点已保留）' : ''}`)
  }

  return {
    canGroup,
    groupSelected,
    ungroupNode,
  }
}
