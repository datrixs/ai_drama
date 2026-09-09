import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  createProject,
  getProjectDetail,
  confirmProject,
  getProjectConfig,
  updateProjectConfig,
  getProjectNovelText,
} from '@/api/project'
import {
  triggerAnalysis,
  getAnalysis,
} from '@/api/project/analyze'

export const useProjectStore = defineStore('project', () => {
  const project = ref(null)
  const analysis = ref(null)
  const projectConfig = ref(null)
  const isLoading = ref(false)
  const currentVersion = ref(null)

  // 计算属性
  const isAnalyzing = computed(() => project.value?.status === 'analyzingStory')
  const isStoryReady = computed(() => project.value?.status === 'storyReady')
  const canEdit = computed(() => project.value?.status === 'projectCreated')
  const canProceed = computed(() =>
    project.value?.status === 'projectCreated' && analysis.value !== null
  )

  // 创建项目
  async function create(data) {
    isLoading.value = true
    try {
      const res = await createProject(data)
      project.value = { id: res.id, status: res.status, create_time: res.create_time }
      return res
    } finally {
      isLoading.value = false
    }
  }

  // 开始首次分析
  async function startAnalysis(projectId) {
    isLoading.value = true
    try {
      const res = await triggerAnalysis(projectId, { adjustment: null })
      if (project.value) {
        project.value.status = 'analyzingStory'
      }
      return res
    } finally {
      isLoading.value = false
    }
  }

  // 调整分析
  async function adjustAnalysis(projectId, adjustment) {
    isLoading.value = true
    try {
      const res = await triggerAnalysis(projectId, { adjustment })
      if (project.value) {
        project.value.status = 'analyzingStory'
      }
      return res
    } finally {
      isLoading.value = false
    }
  }

  // 确认项目设置
  async function confirm(projectId, data) {
    isLoading.value = true
    try {
      const res = await confirmProject(projectId, data)
      if (project.value) {
        project.value.status = res.status
        project.value.title = res.title
        project.value.config = res.config
      }
      return res
    } finally {
      isLoading.value = false
    }
  }

  // 获取项目详情
  async function fetchProject(projectId) {
    const res = await getProjectDetail(projectId)
    project.value = res
    return res
  }

  // 获取分析结果
  async function fetchAnalysis(projectId) {
    const res = await getAnalysis(projectId)
    analysis.value = res
    currentVersion.value = res
    return res
  }

  // // 保存分镜
  // async function updateStoryboard(projectId, storyboard) {
  //   const res = await saveStoryboard(projectId, { storyboard })
  //   if (analysis.value) {
  //     analysis.value.first_ep_storyboard = storyboard
  //   }
  //   return res
  // }

  // 重置
  function reset() {
    project.value = null
    analysis.value = null
    projectConfig.value = null
    isLoading.value = false
    currentVersion.value = null
  }

  // 获取项目配置
  async function fetchProjectConfig(projectId) {
    const res = await getProjectConfig(projectId)
    projectConfig.value = res
    return res
  }

  // 更新项目配置
  async function saveProjectConfig(projectId, data) {
    const res = await updateProjectConfig(projectId, data)
    projectConfig.value = res
    if (project.value) {
      project.value.title = res.title
    }
    return res
  }

  // 获取小说原文
  async function fetchNovelText(projectId) {
    const res = await getProjectNovelText(projectId)
    return res.novel_text || ''
  }

  return {
    project, analysis, projectConfig, isLoading, currentVersion,
    isAnalyzing, isStoryReady, canEdit, canProceed,
    create, startAnalysis, adjustAnalysis, confirm,
    fetchProject, fetchAnalysis,
    fetchProjectConfig, saveProjectConfig, fetchNovelText, reset,
  }
})
