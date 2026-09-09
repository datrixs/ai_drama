<template>
  <el-dropdown trigger="click" @command="handleClick" popper-class="add-asset-dropdown__popper">
    <button class="glass-btn-base glass-btn-primary add-asset-dropdown__trigger">
      <Plus :size="16" />
      <span>新建资产</span>
      <ChevronDown :size="14" class="add-asset-dropdown__arrow" />
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="addCharacter">
          <UserRound :size="16" />
          <span>新建角色</span>
        </el-dropdown-item>
        <el-dropdown-item command="addLocation">
          <ImageIcon :size="16" />
          <span>新建场景</span>
        </el-dropdown-item>
        <el-dropdown-item command="addProp">
          <Diamond :size="16" />
          <span>新建道具</span>
        </el-dropdown-item>
        <el-dropdown-item command="addVoice">
          <Mic :size="16" />
          <span>新建音色</span>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { UserRound, Image as ImageIcon, Diamond, ChevronDown, Plus, Mic } from '@lucide/vue'

const emit = defineEmits(['addCharacter', 'addLocation', 'addProp', 'addVoice'])

const eventMap = {
  addCharacter: () => emit('addCharacter'),
  addLocation: () => emit('addLocation'),
  addProp: () => emit('addProp'),
  addVoice: () => emit('addVoice')
}

function handleClick(type) {
  eventMap[type]()
}
</script>

<style scoped>
.add-asset-dropdown__trigger {
  padding: 8px 16px;
  border-radius: 12px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>

<style>
.add-asset-dropdown__popper {
  min-width: 160px !important;
  padding: 6px 0 !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12) !important;
}

.add-asset-dropdown__popper .el-dropdown-menu {
  padding: 0 !important;
}

.add-asset-dropdown__popper .el-dropdown-menu__item {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  padding: 10px 16px !important;
  font-size: 14px !important;
}
</style>
