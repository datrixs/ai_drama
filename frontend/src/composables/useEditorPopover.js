import { computed } from 'vue'

/**
 * 节点编辑浮层定位：跟随节点位置（节点右侧），用 Teleport 渲染到 body 以逃离 VueFlow 的 transform。
 *
 * @param {object} opts
 * @param {import('vue').Ref<string|null>} opts.editingNodeId
 * @param {import('vue').Ref<any[]>} opts.flowNodes
 * @param {import('vue').Ref<{zoom: number, x: number, y: number}|undefined>} opts.viewport
 */
export function useEditorPopover({ editingNodeId, flowNodes, viewport }) {
  const NODE_W = 240
  const NODE_H = 120
  const POPOVER_W = 380
  const POPOVER_H = 320
  const POPOVER_GAP = 24

  const editorPopoverStyle = computed(() => {
    if (!editingNodeId.value) return { display: 'none' }
    const node = flowNodes.value.find((n) => n.id === editingNodeId.value)
    if (!node) return { display: 'none' }
    const zoom = viewport.value?.zoom ?? 1
    const vx = viewport.value?.x ?? 0
    const vy = viewport.value?.y ?? 0
    const nodeScreenX = node.position.x * zoom + vx
    const nodeScreenY = node.position.y * zoom + vy
    let left = nodeScreenX + NODE_W * zoom + POPOVER_GAP
    let top = nodeScreenY
    if (left + POPOVER_W > window.innerWidth - 8) {
      const altLeft = nodeScreenX - POPOVER_W - POPOVER_GAP
      if (altLeft >= 8) {
        left = altLeft
      } else {
        left = Math.max(8, (window.innerWidth - POPOVER_W) / 2)
      }
    }
    if (top + POPOVER_H > window.innerHeight - 8) {
      top = Math.max(8, window.innerHeight - 8 - POPOVER_H)
    }
    if (top < 8) top = 8
    return {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
      width: `${POPOVER_W}px`,
      height: `${POPOVER_H}px`,
      zIndex: 1000,
    }
  })

  return { editorPopoverStyle }
}
