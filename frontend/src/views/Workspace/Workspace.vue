<template>
  <AppLayout>
    <div class="workspace-page">
      <main class="workspace-main" @click="settingsVisible = false">

        <!-- 左上角项目信息浮标 -->
        <div v-if="store.canEdit" class="project-badge">
          <div class="project-badge-inner">
            <div class="project-badge-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
            </div>
            <div class="project-badge-text">
              <span class="project-badge-name">{{ store.project.title || '未命名项目' }}</span>
            </div>
          </div>
        </div>

        <!-- 胶囊导航 -->
        <CapsuleNav
          v-if="store.canEdit"
          :items="navItems"
          :active-id="activeTab"
          @select="handleTabChange"
        />

        <!-- 右上角操作按钮 -->
        <div v-if="store.canEdit" class="workspace-top-actions">
          <button
            class="glass-btn-base glass-btn-secondary top-action-btn"
            @click.stop="settingsVisible = true"
            title="项目配置"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
            <span class="hidden md:inline">项目配置</span>
          </button>
          <button
            class="glass-btn-base glass-btn-secondary top-action-btn"
            :disabled="refreshing"
            @click="handleRefresh"
            title="刷新"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ 'animate-spin': refreshing }"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/></svg>
            <span class="hidden md:inline"></span>
          </button>
        </div>

        <!-- Loading 状态 -->
        <div v-if="loading || store.isAnalyzing" class="loading-state animate-fadeInDown">
          <div class="loading-inner">
            <img src="/loading.png" alt="" class="loading-img" />
            <p class="loading-text">正在研读故事内核，构思视觉风格...</p>
            <!-- <p v-if="progressStep" class="loading-step">{{ progressStep }}</p> -->
          </div>
        </div>

        <!-- 分析失败状态 -->
        <div v-else-if="isAnalysisFailed" class="error-state animate-fadeIn">
          <div class="error-inner">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-danger-fg)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
            <p class="error-text">故事分析失败，请重试</p>
            <button
              class="glass-btn-base glass-btn-primary retry-btn"
              :disabled="retrying"
              @click="handleRetry"
            >
              <span v-if="retrying" class="btn-loading" />
              <template v-else>重新分析</template>
            </button>
          </div>
        </div>

        <!-- 确认弹窗 -->
        <div v-else-if="store.isStoryReady" class="glass-overlay" @click.self>
          <div class="glass-surface-modal confirm-modal animate-fadeInDown">
            <div class="confirm-header">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--glass-accent-from)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
              <h2 class="confirm-title">确认项目信息</h2>
            </div>

            <div class="confirm-form">
              <label class="confirm-field">
                <span class="field-label">项目名称</span>
                <input
                  v-model="form.title"
                  class="glass-input-base field-input"
                  placeholder="请输入项目名称"
                  maxlength="128"
                  autocomplete="off"
                />
              </label>

              <div class="confirm-row">
                <div class="confirm-field">
                  <span class="field-label">画面比例</span>
                  <select v-model="form.ratio" class="glass-input-base field-select">
                    <option value="21:9">21:9</option>
                    <option value="16:9">16:9</option>
                    <option value="4:3">4:3</option>
                    <option value="1:1">1:1</option>
                    <option value="3:4">3:4</option>
                    <option value="9:16">9:16</option>
                  </select>
                </div>
                <div class="confirm-field">
                  <span class="field-label">画面风格</span>
                  <select v-model="form.style" class="glass-input-base field-select">
                    <option value="american-comic">漫画风</option>
                    <option value="chinese-comic">精致国漫</option>
                    <option value="japanese-anime">日系动漫风</option>
                    <option value="realistic">真人风格</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="confirm-footer">
              <button
                class="glass-btn-base glass-btn-primary confirm-btn"
                :disabled="confirming"
                @click="handleConfirm"
              >
                <span v-if="confirming" class="btn-loading" />
                <template v-else>
                  确认
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                </template>
              </button>
            </div>
          </div>
        </div>

        <!-- 分析结果展示 -->
        <div v-else-if="store.canEdit && store.analysis && activeTab === 'story'" class="analysis-content animate-page-enter">
          <div v-if="!scriptsVisible" class="adjust-section glass-surface-elevated">
            <div class="adjust-header">
              <div class="adjust-header-left">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--glass-accent-from)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M3 12h18"/><path d="m15 6 3-3 3 3"/><path d="M6 9l3 3-3 3"/></svg>
                <span class="adjust-label">调整要求</span>
              </div>
              <div class="adjust-header-right">
                <el-tooltip content="查看原始文本" placement="top" :show-after="300">
                  <button
                    class="glass-btn-base glass-btn-ghost novel-text-btn"
                    :disabled="novelTextLoading"
                    @click="handleViewNovelText"
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
                  </button>
                </el-tooltip>
                <button
                  class="glass-btn-base glass-btn-primary retry-btn"
                  :disabled="!adjustmentText.trim() || store.isAnalyzing"
                  @click="handleAdjust"
                >
                  发送
                </button>
              </div>
            </div>
            <textarea
              v-model="adjustmentText"
              class="adjust-textarea"
              rows="4"
              placeholder="填写希望模型如何调整每集剧本大纲、人物关系与特征、场景描写、道具描写；点「发送」后将在当前小说正文基础上重新跑剧本分析并更新上述四块内容"
            />
          </div>

          <!-- 卡片区域 -->
          <div class="cards-section" :class="{ 'cards-section--shifted': scriptsVisible }">

            <!-- 剧本大纲上方信息栏（步骤2） -->
            <div v-if="scriptsVisible" class="outline-info-bar">
              <span class="outline-ep-count">共 {{ episodeScripts.length }} 集</span>
              <div class="outline-more-wrap">
                <button class="glass-btn-base outline-more-btn" @click="outlineMenuOpen = !outlineMenuOpen">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/></svg>
                </button>
                <Transition name="dropdown">
                  <div v-if="outlineMenuOpen" class="glass-surface-modal outline-more-menu" @click.stop>
                    <button class="outline-menu-item" :disabled="novelTextLoading" @click="handleViewNovelText(); outlineMenuOpen = false">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
                      查看原文
                    </button>
                    <button class="outline-menu-item" @click="handleDownloadScripts(); outlineMenuOpen = false">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>
                      下载剧本
                    </button>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- 剧本大纲&资产解析（合并卡片） -->
            <div class="content-card glass-surface">
              <div class="card-header card-header-clickable" @click="outlineExpanded = !outlineExpanded">
                <div class="card-header-left">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
                  <span>剧本大纲&资产解析</span>
                </div>
                <svg class="collapse-icon" :class="{ 'is-collapsed': !outlineExpanded }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
              </div>
              <div v-show="outlineExpanded" class="card-body">
                <div class="sub-section">
                  <div class="sub-header">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
                    <span>每集剧本大纲</span>
                  </div>
                  <div class="card-text">{{ store.analysis.episode_outlines || '' }}</div>
                </div>
                <div class="sub-section">
                  <div class="sub-header">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    <span>人物关系与特征</span>
                  </div>
                  <div class="card-text">{{ store.analysis.character_profiles || '' }}</div>
                </div>
                <div class="sub-section">
                  <div class="sub-header">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="m9 16 2 2 4-4"/></svg>
                    <span>场景描写</span>
                  </div>
                  <div class="card-text">{{ store.analysis.scene_descriptions || '' }}</div>
                </div>
                <div class="sub-section last">
                  <div class="sub-header">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 8-2 2-1.5-3.7A2 2 0 0 0 15.646 5H8.4a2 2 0 0 0-1.903 1.257L5 10 3 8"/><path d="M2 14h12a2 2 0 0 1 2 2v4"/><path d="M2 10h1"/></svg>
                    <span>道具描写</span>
                  </div>
                  <div class="card-text">{{ store.analysis.prop_descriptions || '' }}</div>
                </div>
              </div>
            </div>

            <!-- 创作分集剧本 -->
            <div v-if="!scriptsVisible" class="create-scripts-wrap">
              <button
                class="glass-btn-base glass-btn-primary create-scripts-btn"
                :disabled="scriptsGenerating"
                @click="handleCreateScripts"
              >
                <template v-if="scriptsGenerating">
                  <span class="btn-loading" />
                  剧本创作中...
                </template>
                <template v-else>
                  创作分集剧本
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
                </template>
              </button>
              <span class="create-scripts-hint">*生成分集剧本后将无法再进行调整</span>
            </div>

            <!-- 分集剧本 -->
            <div v-if="scriptsVisible" class="content-card glass-surface">
              <div class="card-header card-header-clickable" @click="scriptsExpanded = !scriptsExpanded">
                <div class="card-header-left">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--glass-tone-info-fg)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="7" rx="2"/><path d="m2 7 8.7-5a2 2 0 0 1 2.6 0L22 7"/><circle cx="12" cy="14" r="3"/></svg>
                  <span>分集剧本</span>
                </div>
                <svg class="collapse-icon" :class="{ 'is-collapsed': !scriptsExpanded }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
              </div>
              <div v-show="scriptsExpanded" class="card-body">
                <div v-for="ep in episodeScripts" :key="ep.episode" class="episode-script-block">
                  <!-- 待生成 -->
                  <div v-if="ep.status === 'pending'" class="episode-script-header episode-script-pending">
                    <span class="episode-script-title">第 {{ ep.episode }} 集：{{ ep.title }}</span>
                    <span class="ep-script-badge badge-pending">待生成</span>
                  </div>
                  <!-- 生成中 -->
                  <div v-else-if="ep.status === 'generating'" class="episode-script-header episode-script-generating">
                    <span class="episode-script-title">第 {{ ep.episode }} 集：{{ ep.title }}</span>
                    <span class="ep-script-badge badge-generating"><span class="badge-spin" />生成中</span>
                  </div>
                  <!-- 失败 -->
                  <div v-else-if="ep.status === 'failed'" class="episode-script-header episode-script-failed">
                    <span class="episode-script-title">第 {{ ep.episode }} 集：{{ ep.title }}</span>
                    <button class="ep-retry-btn" @click="handleRetryEpisodeScript(ep)">重新生成</button>
                  </div>
                  <!-- 已完成 -->
                  <template v-else>
                    <div class="episode-script-header" @click="expandedEpisodes[ep.episode] = !expandedEpisodes[ep.episode]">
                      <span class="episode-script-title">第 {{ ep.episode }} 集：{{ ep.title }}</span>
                      <svg class="collapse-icon" :class="{ 'is-collapsed': !expandedEpisodes[ep.episode] }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
                    </div>
                    <div v-show="expandedEpisodes[ep.episode]" class="episode-script-body">
                      <div class="card-text">{{ ep.content }}</div>
                    </div>
                  </template>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- 资产库 Tab -->
        <div v-else-if="activeTab === 'asset-library' && store.canEdit" class="asset-library-content animate-page-enter">
          <ProjectAssetLibrary :project-id="projectId" />
        </div>

        <!-- 空状态 -->
        <div v-else-if="!loading" class="empty-state">
          <div class="empty-inner">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--glass-text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
            <p>项目数据加载中...</p>
          </div>
        </div>

        <!-- 剧集 Tab -->
        <div v-if="activeTab === 'episodes' && store.canEdit" class="episodes-section animate-page-enter">
          <div class="episodes-header glass-surface-elevated">
            <div class="episodes-header-left">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--glass-accent-from)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="7" rx="2"/><path d="m2 7 8.7-5a2 2 0 0 1 2.6 0L22 7"/><circle cx="12" cy="14" r="3"/></svg>
              <span class="episodes-label">剧集管理</span>
              <span class="episodes-count">{{ episodes.length }} 集</span>
            </div>
          </div>

          <!-- Loading -->
          <div v-if="loadingEpisodes" class="sb-loading">
            <div class="loading-breathe" />
            <p>加载剧集列表...</p>
          </div>

          <!-- 剧集列表 -->
          <div v-else-if="episodes.length > 0" class="episodes-list">
            <div
              v-for="ep in episodes"
              :key="ep.id"
              class="episode-card glass-surface-elevated"
            >
              <!-- 封面图区域（无视频时显示「暂无视频」占位） -->
              <div class="ep-card-cover">
                <img
                  v-if="ep.cover_url"
                  :src="ep.cover_url"
                  alt="首帧"
                  class="ep-cover-img"
                />
                <div v-else class="ep-cover-placeholder">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                    <rect width="20" height="14" x="2" y="5" rx="2" />
                    <polygon points="10 9 15 12 10 15" />
                  </svg>
                  <span>暂无视频</span>
                </div>
              </div>
              <div class="ep-card-body">
                <div class="ep-card-header">
                  <span class="ep-number">第 {{ ep.episode_number }} 集<template v-if="ep.title">: {{ ep.title }}</template></span>
                  <span class="ep-status" :class="`eps-${ep.status}`">{{ epStatusLabel(ep.status) }}</span>
                </div>
                <p v-if="ep.outline" class="ep-outline">{{ ep.outline }}</p>
                <div class="ep-card-actions">
                  <template v-if="ep.status === 'completed' || ep.status === 'failed'">
                    <button
                      class="glass-btn-base glass-btn-soft ep-action-btn"
                      @click="handleGenerateScript(ep)"
                    >
                      重新生成
                    </button>
                    <button
                      class="glass-btn-base glass-btn-primary ep-action-btn"
                      @click="goToStoryboard(ep)"
                    >
                      进入分镜编辑
                    </button>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-else class="sb-empty">
            <p class="sb-empty-text">暂无剧集数据</p>
            <p class="sb-empty-hint">完成故事分析后将自动生成剧集</p>
          </div>
        </div>

        <!-- 下一步浮动按钮 -->
        <div v-if="(activeTab === 'story' && scriptsVisible) || activeTab === 'asset-library'" class="next-btn-wrapper">
          <button
            class="glass-btn-base glass-btn-primary next-btn"
            :disabled="(activeTab === 'story' && (assetStore.isParsing || scriptsGenerating || !allScriptsDone)) || (activeTab === 'asset-library' && !assetStore.allReady) || nextLoading"
            @click="handleNext"
          >
            <span v-if="(activeTab === 'story' && (assetStore.isParsing || scriptsGenerating)) || nextLoading" class="btn-loading" />
            <template v-else>
              下一步
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
            </template>
          </button>
        </div>

        <!-- 项目设置抽屉 -->
        <ProjectSettingsDrawer
          v-model:visible="settingsVisible"
          :project-id="projectId"
          @config-updated="handleConfigUpdated"
        />

        <!-- 查看原文弹框 -->
        <Teleport to="body">
          <div v-if="novelTextDialogVisible" class="glass-overlay" @click.self="novelTextDialogVisible = false">
            <div class="glass-surface-modal" style="max-width: 780px; width: 90%; height: 80vh; display: flex; flex-direction: column;">
              <div class="modal-header">
                <h3 class="modal-title">原文本内容</h3>
                <button class="modal-close-btn" @click="novelTextDialogVisible = false">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                </button>
              </div>
              <div class="modal-body" style="flex: 1; min-height: 0; padding: 20px 28px 28px; display: flex; flex-direction: column;">
                <div class="novel-text-content" v-loading="novelTextLoading" style="flex: 1; min-height: 0; overflow-y: auto;">
                  <pre class="novel-text-pre">{{ novelTextContent }}</pre>
                </div>
              </div>
            </div>
          </div>
        </Teleport>
      </main>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppLayout from '@/layout/AppLayout.vue'
import { useProjectStore } from '@/store/project'
import { useWebSocket /* , STEP_TEXT */ } from '@/composables/useWebSocket'
import { useProjectAssetWs } from '@/composables/useProjectAssetWs'
import CapsuleNav from '@/components/CapsuleNav.vue'
import ProjectSettingsDrawer from './components/ProjectSettingsDrawer.vue'
import ProjectAssetLibrary from './components/ProjectAssetLibrary/ProjectAssetLibrary.vue'
import { useProjectAssetStore } from '@/store/project_asset'
import { getEpisodes, generateEpisodeScripts, retryEpisodeScript } from '@/api/episode'
import { generateScript as apiGenerateScript, batchGenerateScripts as apiBatchGenerateScripts } from '@/api/video'
import { WSEventType, ScriptTaskStatus } from '@/constants/ws'

const route = useRoute()
const router = useRouter()
const store = useProjectStore()
const assetStore = useProjectAssetStore()
const ws = useWebSocket()

const props = defineProps({ projectId: String })
const handleProjectAssetEvent = useProjectAssetWs(() => props.projectId)

// Tab 导航
const isDirectorMode = computed(() => store.project?.config?.mode === 'director')
const defaultTab = computed(() => (isDirectorMode.value ? 'episodes' : 'story'))
const activeTab = ref(route.query.tab || defaultTab.value)

const assetsParsed = ref(false)

const navItems = computed(() => {
  // 导演模式：只显示剧集 Tab，跳过故事分析与资产库
  if (isDirectorMode.value) {
    return [{ id: 'episodes', label: '剧集', status: 'ready' }]
  }
  const s = store.project?.status
  const laterStage = ['assetGenerating', 'assetsReady', 'producing', 'completed'].includes(s)
  const canAccessAssets = laterStage || assetsParsed.value
  // 剧本生成中时禁用资产库和剧集 Tab
  const scriptsInProgress = scriptsVisible.value && !allScriptsDone.value
  return [
    { id: 'story', label: '故事', status: store.isAnalyzing ? 'processing' : (store.canEdit ? 'ready' : 'empty') },
    { id: 'asset-library', label: '资产库', status: canAccessAssets ? 'ready' : 'empty', disabled: !canAccessAssets || scriptsInProgress, disabledLabel: scriptsInProgress ? '请先完成分集剧本创作' : '完成故事分析后解锁' },
    { id: 'episodes', label: '剧集', status: canAccessAssets ? 'ready' : 'empty', disabled: !canAccessAssets || scriptsInProgress, disabledLabel: scriptsInProgress ? '请先完成分集剧本创作' : '资产库完成后解锁' },
  ]
})

function handleTabChange(tabId) {
  if (tabId === 'episodes') {
    router.push(`/workspace/${props.projectId}/episodes`)
    return
  }
  activeTab.value = tabId
  router.replace({ query: { ...route.query, tab: tabId } })
}

const loading = ref(true)
const confirming = ref(false)
const refreshing = ref(false)
const retrying = ref(false)
const nextLoading = ref(false)
const adjustmentText = ref('')
const novelTextDialogVisible = ref(false)
const novelTextContent = ref('')
const novelTextLoading = ref(false)
const settingsVisible = ref(false)
const episodes = ref([])
const loadingEpisodes = ref(false)
const outlineExpanded = ref(true)
const scriptsVisible = ref(false)
const outlineMenuOpen = ref(false)
const scriptsGenerating = ref(false)
const scriptsExpanded = ref(true)
const expandedEpisodes = reactive({})
const episodeScripts = ref([])

async function handleCreateScripts() {
  scriptsGenerating.value = true
  scriptsVisible.value = true
  scriptsExpanded.value = true
  outlineExpanded.value = false

  try {
    // 先解析资产（将大纲/人物/道具/场景/剧集写入数据库表）
    await assetStore.parseAssets(props.projectId)
    assetsParsed.value = true

    // 刷新剧集列表（parseAssets 刚创建了 Episode 记录）
    await fetchEpisodes()

    // 初始化前端剧集列表状态
    episodeScripts.value = episodes.value.map(ep => ({
      episode: ep.episode_number,
      title: ep.title || '',
      status: 'pending',
      content: '',
    }))

    await generateEpisodeScripts(props.projectId)
    // 后端标记为 generating，前端通过 WS 事件更新状态
    episodeScripts.value.forEach(ep => { ep.status = 'generating' })
  } catch {
    scriptsGenerating.value = false
  }
}

async function handleRetryEpisodeScript(ep) {
  ep.status = 'generating'
  try {
    const epData = episodes.value.find(e => e.episode_number === ep.episode)
    if (!epData) throw new Error('剧集不存在')
    await retryEpisodeScript(props.projectId, epData.id)
  } catch {
    ep.status = 'failed'
  }
}

function handleDownloadScripts() {
  const lines = episodeScripts.value
    .filter(ep => ep.status === 'done' && ep.content)
    .map(ep => `===== 第${ep.episode}集：${ep.title} =====\n${ep.content}`)
    .join('\n\n')
  if (!lines) {
    ElMessage.warning('暂无已完成的剧本可下载')
    return
  }
  const blob = new Blob([lines], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.project?.title || '剧本'}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

function handleOutlineMenuClickOutside(e) {
  if (outlineMenuOpen.value && !e.target.closest('.outline-more-wrap')) {
    outlineMenuOpen.value = false
  }
}

async function fetchEpisodeScriptContent(epNum) {
  try {
    const res = await getEpisodes(props.projectId)
    const updated = res.find(e => e.episode_number === epNum)
    if (updated && updated.episode_script) {
      const ep = episodeScripts.value.find(e => e.episode === epNum)
      if (ep) ep.content = updated.episode_script
    }
  } catch {}
}

const allScriptsDone = computed(() => {
  return episodeScripts.value.length > 0 && episodeScripts.value.every(ep => ep.status === 'done')
})

const isAnalysisFailed = computed(() => {
  return store.project?.status === 'draft' && store.project?.analysis_status === 'failed'
})

const form = ref({
  title: '',
  ratio: '9:16',
  style: 'realistic',
})

const formatEpisodeOutlines = computed(() => {
  let outlines = store.analysis?.episode_outlines
  if (!outlines) return ''
  if (typeof outlines === 'string') {
    try { outlines = JSON.parse(outlines) } catch { return outlines }
  }
  if (!Array.isArray(outlines)) return ''
  return outlines.map(ep => `第${ep.episode_number}集：${ep.title || ''}\n${ep.summary || ''}`).join('\n\n')
})

async function loadProject() {
  loading.value = true
  try {
    await store.fetchProject(props.projectId)
    const s = store.project?.status

    // 导演模式：跳过故事分析、资产加载，直接重定向到 EpisodePage
    if (isDirectorMode.value) {
      loading.value = false
      router.replace(`/workspace/${props.projectId}/episodes`)
      return
    }

    if (s === 'draft') {
      // 分析曾失败则不自动触发，交由用户手动重试
      if (store.project?.analysis_status !== 'failed') {
        await store.startAnalysis(props.projectId)
      }
    } else if (s === 'analyzingStory') {
      // 分析中，尝试获取已有部分结果（不报错）
      try { await store.fetchAnalysis(props.projectId) } catch {}
    } else if (s === 'storyReady' || s === 'projectCreated') {
      // 分析完成或已确认，获取分析结果
      try { await store.fetchAnalysis(props.projectId) } catch {}
      // 检测已有资产，自动解锁资产库tab
      if (s === 'projectCreated') {
        try {
          await assetStore.fetchAssets(props.projectId)
          if (assetStore.stats.total > 0) {
            assetsParsed.value = true
          }
        } catch {}
      }
      const laterStage = ['assetGenerating', 'assetsReady', 'producing', 'completed'].includes(s)
      if (laterStage || route.query.tab === 'asset-library') {
        assetsParsed.value = true
      }
    }

    if (store.canEdit) {
      try { await store.fetchProjectConfig(props.projectId) } catch {}
    }

    // 预填表单
    if (store.project?.title) form.value.title = store.project.title
    if (store.project?.config?.video_ratio) form.value.ratio = store.project.config.video_ratio
    if (store.project?.config?.art_style) form.value.style = store.project.config.art_style
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}

let removeWsListener = null
let pollTimer = null

// ============ 轮询降级 ============
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!store.isAnalyzing && !store.isStoryReady) return
    try {
      await store.fetchProject(props.projectId)
      if ((store.isStoryReady || store.canEdit) && !store.analysis) {
        await store.fetchAnalysis(props.projectId)
      }
    } catch {}
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// WS 连接状态变化时切换轮询
watch(ws.connected, (isConnected) => {
  if (isConnected) {
    stopPolling()
  } else if (store.isAnalyzing) {
    startPolling()
  }
})

function setupWebSocket() {
  const project = store.project
  if (!project) return
  const userId = project.user_id || project.create_uid
  if (!userId) return

  const handleEvent = async (event) => {
    if (event.project_id && event.project_id !== props.projectId) return

    // 委托处理项目资产库相关事件（批量同步、生成进度、自动同步）
    await handleProjectAssetEvent(event)

    switch (event.event_type) {
      // case 'analysis_progress':
      //   progressStep.value = STEP_TEXT[event.data?.step] || `${event.data?.step || ''} ${event.data?.progress || 0}%`
      //   break
      case 'analysis_completed':
        // progressStep.value = ''
        await store.fetchProject(props.projectId)
        await store.fetchAnalysis(props.projectId)
        break
      case 'analysis_failed':
        // progressStep.value = ''
        await store.fetchProject(props.projectId)
        break
      case 'adjustment_completed':
        await store.fetchProject(props.projectId)
        await store.fetchAnalysis(props.projectId)
        break
      case 'adjustment_failed':
        await store.fetchProject(props.projectId)
        break
      // 资产库事件
      case 'project_asset_parse_completed':
        if (activeTab.value === 'asset-library') {
          await assetStore.fetchAssets(props.projectId)
        }
        break
      case 'project_batch_generation_completed':
        assetStore.fetchAssets(props.projectId)
        break
      case WSEventType.SCRIPT_PROGRESS: {
        const sd = event.data || {}
        const epNum = sd.episode_number
        if (epNum) {
          const ep = episodes.value.find(e => e.episode_number === epNum)
          if (ep) {
            if (sd.status === ScriptTaskStatus.GENERATING) ep.status = 'generating'
            else if (sd.status === ScriptTaskStatus.COMPLETED) ep.status = 'completed'
            else if (sd.status === ScriptTaskStatus.FAILED) ep.status = 'failed'
          }
        }
        break
      }
      case WSEventType.EPISODE_SCRIPT_PROGRESS: {
        const sd = event.data || {}
        const epNum = sd.episode_number
        if (epNum) {
          const ep = episodeScripts.value.find(e => e.episode === epNum)
          if (ep) {
            if (sd.status === 'generating') ep.status = 'generating'
            else if (sd.status === 'completed') {
              ep.status = 'done'
              fetchEpisodeScriptContent(epNum)
            }
            else if (sd.status === 'failed') ep.status = 'failed'
          }
          if (sd.status === 'completed' || sd.status === 'failed') {
            scriptsGenerating.value = episodeScripts.value.some(
              e => e.status === 'generating' || e.status === 'pending'
            )
          }
        }
        break
      }
    }
  }

  removeWsListener = ws.onEvent(handleEvent)
  ws.connect(userId)
}

async function handleConfirm() {
  confirming.value = true
  try {
    await store.confirm(props.projectId, { ...form.value })
    await store.fetchAnalysis(props.projectId)
    ElMessage.success('项目创建成功')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    confirming.value = false
  }
}

async function handleViewNovelText() {
  if (novelTextContent.value) {
    novelTextDialogVisible.value = true
    return
  }
  novelTextLoading.value = true
  novelTextDialogVisible.value = true
  try {
    novelTextContent.value = await store.fetchNovelText(props.projectId)
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    novelTextLoading.value = false
  }
}

async function handleAdjust() {
  if (!adjustmentText.value.trim()) return
  try {
    await store.adjustAnalysis(props.projectId, adjustmentText.value.trim())
    adjustmentText.value = ''
    ElMessage.success('已提交调整请求')
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await store.fetchProject(props.projectId)
    if (store.canEdit || store.isStoryReady) {
      try { await store.fetchAnalysis(props.projectId) } catch {}
    }
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    setTimeout(() => { refreshing.value = false }, 600)
  }
}

async function handleNext() {
  if (activeTab.value === 'story') {
    // 故事Tab → 资产库Tab：资产已在"创作分集剧本"时解析，直接切换
    activeTab.value = 'asset-library'
    router.replace({ query: { ...route.query, tab: 'asset-library' } })
  } else if (activeTab.value === 'asset-library') {
    // 资产库Tab → 剧集页：检查是否有未生成过分镜的剧集
    nextLoading.value = true
    try {
      const epList = await getEpisodes(props.projectId) || []
      const hasPending = epList.some(ep => ep.status === 'pending')
      if (hasPending) {
        await apiBatchGenerateScripts(props.projectId)
      }
    } catch {
      // 批量生成触发失败不阻塞跳转
    } finally {
      nextLoading.value = false
    }
    router.push(`/workspace/${props.projectId}/episodes`)
  }
}

async function handleRetry() {
  retrying.value = true
  try {
    await store.startAnalysis(props.projectId)
    ElMessage.success('已重新开始分析')
  } catch {
    // 错误提示由 request 拦截器统一处理
  } finally {
    retrying.value = false
  }
}

function handleConfigUpdated(configData) {
  store.projectConfig = configData
}

// ============ 剧集管理 ============

function epStatusLabel(status) {
  const map = {
    pending: '待生成',
    generating: '生成中',
    completed: '生成完成',
    failed: '生成失败',
  }
  return map[status] || status
}

async function fetchEpisodes() {
  loadingEpisodes.value = true
  try {
    const res = await getEpisodes(props.projectId)
    episodes.value = res || []

    // 页面刷新时恢复剧本生成状态
    if (episodes.value.length > 0) {
      const hasScriptProgress = episodes.value.some(
        ep => ep.episode_script_status && ep.episode_script_status !== 'pending'
      )
      if (hasScriptProgress) {
        scriptsVisible.value = true
        episodeScripts.value = episodes.value.map(ep => ({
          episode: ep.episode_number,
          title: ep.title || '',
          status: ep.episode_script_status === 'completed' ? 'done'
            : ep.episode_script_status === 'generating' ? 'generating'
            : ep.episode_script_status === 'failed' ? 'failed'
            : 'pending',
          content: ep.episode_script || '',
        }))
        scriptsGenerating.value = episodeScripts.value.some(
          e => e.status === 'generating' || e.status === 'pending'
        )
      }
    }
  } catch {
    episodes.value = []
  } finally {
    loadingEpisodes.value = false
  }
}

async function handleGenerateScript(ep) {
  try {
    await apiGenerateScript(props.projectId, ep.id)
    ep.status = 'generating'
    ElMessage.success(`第 ${ep.episode_number} 集脚本生成任务已提交`)
  } catch {
    // 错误提示由 request 拦截器统一处理
  }
}

function goToStoryboard(ep) {
  router.push({
    path: `/workspace/${props.projectId}/episodes/${ep.id}/storyboard`,
    query: { episodeNumber: ep.episode_number },
  })
}

onMounted(async () => {
  await loadProject()
  setupWebSocket()
  // 加载剧集列表
  if (store.canEdit) {
    await fetchEpisodes()
  }
  // WS 未连接时启动轮询降级
  if (!ws.connected.value && store.isAnalyzing) {
    startPolling()
  }
  document.addEventListener('click', handleOutlineMenuClickOutside)
})
onUnmounted(() => {
  if (removeWsListener) removeWsListener()
  stopPolling()
  store.reset()
  assetStore.reset()
  document.removeEventListener('click', handleOutlineMenuClickOutside)
})
</script>

<style scoped>
.workspace-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--glass-bg-canvas);
}

.workspace-main {
  flex: 1;
  overflow-y: auto;
  position: relative;
  padding: 5rem 1rem 6rem;
  max-width: 56rem;
  margin: 0 auto;
  width: 100%;
}

/* ===== 左上角项目浮标 ===== */
.project-badge {
  position: fixed;
  top: 5rem;
  left: 1.5rem;
  z-index: 40;
  animation: fadeInDown 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.project-badge-inner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 1.5rem;
  background: var(--glass-bg-surface-strong);
  border: 1px solid var(--glass-stroke-soft);
  box-shadow: var(--glass-shadow-sm);
  backdrop-filter: blur(var(--glass-blur-lg));
}

.project-badge-icon {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  background: var(--glass-bg-muted);
  color: var(--glass-tone-info-fg);
  flex-shrink: 0;
}

.project-badge-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.project-badge-name {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--glass-text-primary);
}

.project-badge-sub {
  font-size: 0.75rem;
  color: var(--glass-text-secondary);
}

/* ===== 右上角操作按钮 ===== */
.workspace-top-actions {
  position: fixed;
  top: 6rem;
  right: 1.5rem;
  z-index: 40;
  display: flex;
  gap: 0.75rem;
  animation: fadeInDown 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.top-action-btn {
  padding: 0.75rem 1rem;
  border-radius: 1.5rem;
  font-size: 0.875rem;
  gap: 0.375rem;
}

.top-action-btn:disabled {
  opacity: 0.6;
  cursor: wait;
}

/* ===== Loading 状态 ===== */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: min(28rem, 60vh);
}

.loading-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.loading-img {
  width: 120px;
  height: 120px;
  object-fit: contain;
  animation: loading-breathe 3s ease-in-out infinite;
}

.loading-text {
  font-size: 0.75rem;
  color: var(--glass-text-tertiary);
  text-align: center;
}

/* .loading-step {
  font-size: 0.6875rem;
  color: var(--glass-accent-from);
  font-family: monospace;
} */

/* ===== 确认弹窗 ===== */
.confirm-modal {
  max-width: 28rem;
  width: 90%;
  padding: 1.5rem;
}

.confirm-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.confirm-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--glass-text-primary);
}

.confirm-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.confirm-field {
  display: flex;
  flex-direction: column;
}

.field-label {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--glass-text-primary);
  letter-spacing: 0.01em;
  display: block;
  margin-bottom: 0.375rem;
}

.field-input, .field-select {
  height: 2.5rem;
  padding: 0 0.75rem;
  font-size: 0.875rem;
}

.confirm-row {
  display: flex;
  gap: 1rem;
}

.confirm-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.25rem;
}

.confirm-btn {
  padding: 0.5rem 1.25rem;
  gap: 0.375rem;
}

.btn-loading {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ===== 调整区域 ===== */
.adjust-section {
  border-radius: var(--glass-radius-lg);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.adjust-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.adjust-header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.adjust-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.novel-text-btn {
  height: 40px;
  padding: 0 16px;
  font-size: 14px;
  flex-shrink: 0;
}

.novel-text-content {
  padding: 4px 0;
}

.novel-text-pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 0.875rem;
  line-height: 1.7;
  color: var(--glass-text-primary);
  margin: 0;
}

.adjust-label {
  font-weight: 700;
  font-size: 0.875rem;
  color: var(--glass-text-primary);
}

.adjust-hint {
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--glass-text-tertiary);
}

.adjust-textarea {
  width: 100%;
  border-radius: var(--glass-radius-lg);
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-muted);
  padding: 0.75rem 1rem;
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--glass-text-primary);
  outline: none;
  resize: vertical;
  font-family: inherit;
}

.adjust-textarea::placeholder {
  color: var(--glass-text-tertiary);
}

.adjust-textarea:focus {
  border-color: var(--glass-stroke-focus);
  box-shadow: 0 0 0 3px var(--glass-focus-ring);
  background: var(--glass-bg-surface-strong);
}

/* ===== 大纲信息栏（步骤2） ===== */
.outline-info-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1.25rem;
}

.outline-ep-count {
  font-size: 1.8rem;
  font-weight: 600;
  color: var(--glass-text-secondary);
}

.outline-more-wrap {
  position: relative;
}

.outline-more-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  margin-right: -7px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
  background: var(--glass-bg-muted);
  border: 1px solid var(--glass-stroke-base);
}

.outline-more-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 50;
  padding: 6px;
  min-width: 140px;
}

.outline-menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 0.8125rem;
  color: var(--glass-text-secondary);
  cursor: pointer;
  transition: background 0.15s;
}

.outline-menu-item:hover {
  background: var(--glass-bg-muted);
}

.outline-menu-item:disabled {
  opacity: 0.5;
  cursor: wait;
}

/* ===== 内容卡片 ===== */
.cards-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 2rem;
}
.cards-section--shifted {
  margin-top: 3rem;
}

.create-scripts-wrap {
  display: flex;
  align-items: center;
  gap: 0.625rem;
}

.create-scripts-btn {
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem 1.5rem;
  border-radius: var(--glass-radius-lg);
  font-size: 0.8125rem;
  font-weight: 600;
  flex-shrink: 0;
}

.create-scripts-hint {
  font-size: 0.75rem;
  color: #dc2626;
  white-space: nowrap;
}

.scripts-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2.5rem 0;
  gap: 0.75rem;
}

.scripts-loading p {
  font-size: 0.8125rem;
  color: var(--glass-text-tertiary);
}

.content-card {
  border-radius: var(--glass-radius-lg);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--glass-text-primary);
  padding: 0.875rem 1.25rem;
  border-bottom: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-muted);
}

.card-header-clickable {
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
}

.card-header-clickable:hover {
  background: var(--glass-bg-surface-strong);
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.collapse-icon {
  transition: transform 0.25s ease;
  flex-shrink: 0;
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

.card-header-right {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  cursor: pointer;
  padding: 0.25rem;
}

.card-body {
  padding: 0.875rem 1.25rem;
}

/* ===== 子区块 ===== */
.sub-section {
  padding-bottom: 1rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--glass-stroke-base);
}

.sub-section.last {
  padding-bottom: 0;
  margin-bottom: 0;
  border-bottom: none;
}

.sub-header {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-text-secondary);
  margin-bottom: 0.5rem;
}

/* ===== 分集剧本 ===== */
.episode-script-block {
  margin-bottom: 0.75rem;
}

.episode-script-block:last-child {
  margin-bottom: 0;
}

.episode-script-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.625rem 0.875rem;
  background: var(--glass-bg-muted);
  border-radius: var(--glass-radius-md);
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
}

.episode-script-header:hover {
  background: var(--glass-bg-surface-strong);
}

.episode-script-pending,
.episode-script-generating,
.episode-script-failed {
  cursor: default;
}

.episode-script-pending:hover,
.episode-script-generating:hover,
.episode-script-failed:hover {
  background: var(--glass-bg-muted);
}

.episode-script-failed {
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.ep-retry-btn {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  border: 1px solid var(--glass-stroke-base);
  background: var(--glass-bg-surface-strong);
  color: var(--glass-text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.ep-retry-btn:hover {
  border-color: var(--glass-stroke-focus);
  box-shadow: 0 0 0 3px var(--glass-focus-ring);
}

.ep-script-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  flex-shrink: 0;
}

.badge-pending {
  color: var(--glass-text-tertiary);
  background: var(--glass-bg-muted);
  border: 1px solid var(--glass-stroke-base);
}

.badge-generating {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.badge-spin {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(245, 158, 11, 0.3);
  border-top-color: #f59e0b;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.episode-script-title {
  font-weight: 700;
  font-size: 13px;
  color: var(--glass-text-primary);
}

.episode-script-body {
  padding: 0.75rem 0.25rem 0;
}

.card-text {
  font-size: 0.8125rem;
  line-height: 1.7;
  color: var(--glass-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== 分镜列表 ===== */
.storyboard-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.storyboard-item {
  background: var(--glass-bg-muted);
  border-radius: var(--glass-radius-md);
  padding: 0.875rem 1rem;
  border: 1px solid var(--glass-stroke-base);
  transition: border-color 0.2s ease;
}

.storyboard-item:hover {
  border-color: var(--glass-stroke-focus);
}

.scene-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.scene-tag {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
  background: var(--glass-tone-info-bg);
  color: var(--glass-tone-info-fg);
}

.scene-location {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--glass-text-primary);
}

.scene-meta {
  font-size: 0.6875rem;
  color: var(--glass-text-tertiary);
  background: var(--glass-tone-neutral-bg);
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
}

.scene-action {
  font-size: 0.8125rem;
  color: var(--glass-text-secondary);
  line-height: 1.6;
  margin-bottom: 0.25rem;
}

.scene-detail {
  font-size: 0.75rem;
  color: var(--glass-text-tertiary);
  line-height: 1.5;
  margin-top: 0.25rem;
}

.scene-detail strong {
  color: var(--glass-text-secondary);
}

/* ===== 资产库内容区 ===== */
.asset-library-content {
  margin-top: 1.5rem;
}

/* ===== 下一步按钮 ===== */
.next-btn-wrapper {
  position: fixed;
  bottom: max(1rem, env(safe-area-inset-bottom, 1rem));
  right: 1.5rem;
  z-index: 40;
}

.next-btn {
  min-width: 5.5rem;
  padding: 0.75rem 1.75rem;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
  gap: 0.375rem;
  box-shadow: 0 10px 36px rgba(0, 0, 0, 0.18);
}

.next-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

/* ===== 空状态 ===== */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: min(28rem, 60vh);
}

/* ===== 分析失败状态 ===== */
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: min(28rem, 60vh);
}

.error-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.error-text {
  color: var(--glass-tone-danger-fg);
  font-size: 0.875rem;
}

.retry-btn {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  flex-shrink: 0;
}

.empty-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.empty-inner p {
  color: var(--glass-text-tertiary);
  font-size: 0.875rem;
}

/* ===== 动画 ===== */
@keyframes loading-breathe {
  0%, 100% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.08); opacity: 1; }
}

/* ===== 剧集列表 ===== */
.episodes-section {
  max-width: 56rem;
  margin: 0 auto;
  width: 100%;
}

.episodes-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: var(--glass-radius-lg);
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
}

.episodes-header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.episodes-label {
  font-weight: 700;
  font-size: 0.875rem;
  color: var(--glass-text-primary);
}

.episodes-count {
  font-size: 0.75rem;
  color: var(--glass-text-tertiary);
  background: var(--glass-bg-muted);
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
}

.episodes-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.episode-card {
  padding: 0;
  border-radius: var(--glass-radius-lg);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: default;
  overflow: hidden;
}

.episode-card:hover {
  box-shadow: var(--glass-shadow-lg);
  border-color: var(--glass-stroke-strong);
}

.ep-card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--glass-bg-muted, rgba(244, 247, 252, 0.6));
  overflow: hidden;
  border-bottom: 1px solid rgba(111, 126, 153, 0.08);
}
.ep-cover-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ep-cover-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  width: 100%;
  height: 100%;
  padding: 0.5rem;
  background:
    radial-gradient(circle at 50% 40%, rgba(47, 123, 255, 0.10), transparent 70%),
    linear-gradient(135deg, rgba(226, 232, 240, 0.45), rgba(203, 213, 225, 0.25));
  color: rgba(100, 116, 139, 0.85);
}
.ep-cover-placeholder svg { opacity: 0.65; }
.ep-cover-placeholder span {
  font-size: 0.65rem;
  letter-spacing: 1px;
  color: rgba(100, 116, 139, 0.75);
}

.ep-card-body {
  padding: 1.25rem;
}

.ep-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.ep-number {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--glass-text-primary);
}

.ep-status {
  font-size: 0.7rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
}
.ep-status.eps-pending { color: var(--glass-text-tertiary); background: var(--glass-bg-muted); }
.ep-status.eps-generating { color: #f59e0b; background: rgba(245,158,11,0.1); }
.ep-status.eps-completed { color: #22c55e; background: rgba(34,197,94,0.1); }
.ep-status.eps-failed { color: #ef4444; background: rgba(239,68,68,0.1); }

.ep-outline {
  font-size: 0.8125rem;
  color: var(--glass-text-secondary);
  line-height: 1.6;
  margin: 0 0 1rem;
}

.ep-card-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: auto;
}

.ep-action-btn {
  height: 36px;
  padding: 0 16px;
  font-size: 13px;
}

.sb-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 0;
  color: var(--glass-text-tertiary);
  gap: 0.75rem;
}

.sb-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 0;
  color: var(--glass-text-tertiary);
  gap: 0.5rem;
}

.sb-empty-text {
  font-size: 0.95rem;
  color: var(--glass-text-secondary);
  margin: 0;
}

.sb-empty-hint {
  font-size: 0.85rem;
  margin: 0;
}
</style>
