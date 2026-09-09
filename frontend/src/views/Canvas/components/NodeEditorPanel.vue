<template>
  <div
    ref="panelRootRef"
    class="ne-panel"
    :class="[`ne-type-${nodeType}`]"
    @click="onPanelClickCloseMenu"
  >
    <!-- 顶部操作栏：节点类型 + 清空 + 收起 -->
    <div class="ne-topbar">
      <div class="ne-topbar-left">
        <span class="ne-type-dot" :title="`${typeLabel}节点`"></span>
        <input
          ref="titleInputRef"
          v-model="titleDraft"
          class="ne-title-input"
          type="text"
          :placeholder="`未命名${typeLabel}节点`"
          spellcheck="false"
          maxlength="60"
          @keydown.enter.prevent="onTitleCommit"
          @keydown.esc.prevent="onTitleCancel"
          @blur="onTitleCommit"
        />
        <span v-if="outputUrl" class="ne-status-pill">{{ statusBadgeText }}</span>
      </div>

      <div class="ne-topbar-right">
        <button class="ne-icon-btn" type="button" title="生成历史" @click="$emit('open-history')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /><path d="M12 7v5l3 2" />
          </svg>
        </button>

        <button class="ne-icon-btn" type="button" title="清空 prompt" @click="clearPrompt">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m7 21-4.3-4.3c-.9-.9-.9-2.5 0-3.4l9.6-9.6c.9-.9 2.5-.9 3.4 0l5.6 5.6c.9.9.9 2.5 0 3.4l-9.6 9.6c-.9.9-2.5.9-3.4 0Z" />
            <path d="m22 10-5-5" />
            <path d="M9 13l-3 3" />
          </svg>
        </button>

        <button class="ne-icon-btn" type="button" title="删除节点" @click="$emit('delete')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>

        <button class="ne-icon-btn ne-close-btn" type="button" title="收起（Esc）" @click="$emit('close')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
            <path d="M18 6 6 18" /><path d="m6 6 12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 已生成/已导入的图片/视频缩略图（点击放大查看原图） -->
    <div
      v-if="outputUrl && (isImageNode || isVideoNode)"
      class="ne-preview"
      title="点击放大查看"
      @click="openPreview"
    >
      <img v-if="isImageNode" :src="outputUrl" class="ne-preview-img" alt="" />
      <video v-else :src="outputUrl" class="ne-preview-img ne-preview-video-thumb" muted />
      <span class="ne-preview-zoom-hint">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /><path d="M11 8v6" /><path d="M8 11h6" />
        </svg>
      </span>
    </div>

    <!-- 已上传的音频预览 -->
    <div v-if="isAudioNode && outputUrl" class="ne-audio-preview">
      <audio :src="outputUrl" controls preload="metadata" />
      <div v-if="audioName" class="ne-audio-name" :title="audioName">{{ audioName }}</div>
    </div>

    <!-- 编辑区：上方 prompt + 下方控件（紧凑竖排） -->
    <div class="ne-body">
      <div class="ne-prompt-wrap">
        <template v-if="isTextNode">
          <div class="ne-body-area">
            <CanvasBodyEditor
              v-model:html="bodyHtml"
              :placeholder="bodyPlaceholder"
              @blur="scheduleSave"
            />
          </div>
          <div class="ne-prompt-area">
            <textarea
              v-model="promptDraft"
              class="ne-prompt-input"
              :placeholder="promptPlaceholder"
              @keydown.ctrl.enter="onSubmit"
              @keydown.meta.enter="onSubmit"
            ></textarea>
          </div>
        </template>
        <template v-else-if="isVideoNode">
          <div v-if="referencedNodes.length" class="ne-ref-area">
            <div class="ne-ref-thumbs">
              <div v-for="ref in referencedNodes" :key="ref.tokenKey" class="ne-ref-thumb-cell">
                <div
                  class="ne-ref-thumb"
                  :class="[`ne-ref-thumb-${ref.node_type}`, { 'ne-ref-thumb-audio-card': ref.node_type === 'audio' }]"
                  :title="ref.title"
                  @click="onFocusItem(ref.id)"
                >
                  <!-- 音频：横向 chip（图标 + 名称 + 序号），区别于图片缩略图 -->
                  <div v-if="ref.node_type === 'audio'" class="ne-ref-audio">
                    <span class="ne-ref-audio-icon">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                    </span>
                    <span class="ne-ref-audio-body">
                      <span class="ne-ref-audio-name">{{ ref.title || '未命名音频' }}</span>
                      <span class="ne-ref-audio-tag">音频{{ ref.audioIdx }}</span>
                    </span>
                  </div>
                  <!-- 视频：封面图（优先 thumbnail_url）或视频首帧，叠加播放图标 -->
                  <div v-else-if="ref.node_type === 'video'" class="ne-ref-video">
                    <img v-if="ref.thumbnailUrl" :src="ref.thumbnailUrl" :alt="ref.title || ''" />
                    <video v-else-if="ref.previewUrl" :src="`${ref.previewUrl}#t=0.1`" muted preload="metadata" />
                    <span class="ne-ref-video-play">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20"/></svg>
                    </span>
                  </div>
                  <!-- 图片预览 -->
                  <img v-else-if="ref.previewUrl" :src="ref.previewUrl" :alt="ref.title || ''" />
                  <!-- 文本 -->
                  <span v-else-if="ref.node_type === 'text'" class="ne-ref-text">{{ ref.previewText }}</span>
                  <!-- 其他无预览资源：占位图标 -->
                  <span v-else class="ne-ref-empty-icon" :class="`ne-ref-empty-${ref.node_type}`">
                    <svg v-if="ref.node_type === 'image'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
                    <svg v-else-if="ref.node_type === 'video'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m10 8 6 4-6 4z"/></svg>
                    <svg v-else-if="ref.node_type === 'audio'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                    <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
                  </span>
                  <button
                    class="ne-ref-remove"
                    type="button"
                    title="移除引用"
                    @click.stop="removeReference(ref)"
                  >×</button>
                  <span v-if="showRoleFor(ref)" class="ne-ref-role" :data-role="ref.role">{{ ROLE_LABEL[ref.role] || '参' }}</span>
                </div>
                <button
                  v-if="showSwapButton && ref.imageIdx === 1"
                  class="ne-ref-swap"
                  type="button"
                  title="交换首尾帧"
                  @click="swapFirstLastFrames"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M7 16l-4-4 4-4"/><path d="M17 8l4 4-4 4"/><path d="M3 12h18"/></svg>
                </button>
              </div>
            </div>
          </div>
          <div class="ne-prompt-area is-full">
            <PromptMentionEditor
              ref="videoPromptEditorRef"
              v-model:tokens="promptTokens"
              :available-nodes="availableNodes"
              :placeholder="promptPlaceholder"
              @focus-item="onFocusItem"
            />
          </div>
        </template>
        <template v-else-if="isImageNode">
          <div v-if="referencedNodes.length" class="ne-ref-area">
            <div class="ne-ref-thumbs">
              <div
                v-for="ref in referencedNodes"
                :key="ref.tokenKey"
                class="ne-ref-thumb"
                :class="[`ne-ref-thumb-${ref.node_type}`]"
                :title="ref.title"
                @click="onFocusItem(ref.id)"
              >
                <img v-if="ref.previewUrl" :src="ref.previewUrl" :alt="ref.title || ''" />
                <span v-else-if="ref.node_type === 'text'" class="ne-ref-text">{{ ref.previewText }}</span>
                <span v-else class="ne-ref-empty-icon" :class="`ne-ref-empty-${ref.node_type}`">
                  <svg v-if="ref.node_type === 'image'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>
                  <svg v-else-if="ref.node_type === 'video'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m10 8 6 4-6 4z"/></svg>
                  <svg v-else-if="ref.node_type === 'audio'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>
                </span>
                <button
                  class="ne-ref-remove"
                  type="button"
                  title="移除引用"
                  @click.stop="removeReference(ref)"
                >×</button>
                <span v-if="showRoleFor(ref)" class="ne-ref-role" :data-role="ref.role">{{ ROLE_LABEL[ref.role] || '参' }}</span>
              </div>
            </div>
          </div>
          <div class="ne-prompt-area is-full">
            <PromptMentionEditor
              ref="imagePromptEditorRef"
              v-model:tokens="promptTokens"
              :available-nodes="availableNodes"
              :placeholder="promptPlaceholder"
              @focus-item="onFocusItem"
            />
          </div>
        </template>
        <template v-else-if="isAudioNode">
          <div class="ne-audio-upload-area">
            <div v-if="outputUrl" class="ne-audio-uploaded">
              <div class="ne-audio-uploaded-info">
                <span class="ne-audio-uploaded-icon">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" />
                  </svg>
                </span>
                <span class="ne-audio-uploaded-name" :title="audioName">{{ audioName || '已上传音频' }}</span>
              </div>
              <button class="ne-audio-reupload-btn" type="button" :disabled="uploading" @click="onUploadClick">
                {{ uploading ? '上传中…' : '重新上传' }}
              </button>
            </div>
            <button
              v-else
              class="ne-audio-upload-btn"
              type="button"
              :disabled="uploading"
              @click="onUploadClick"
            >
              <span class="ne-audio-upload-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </span>
              <span class="ne-audio-upload-text">{{ uploading ? '上传中…' : '点击上传音频文件' }}</span>
              <span class="ne-audio-upload-hint">支持 MP3、WAV、M4A、OGG</span>
            </button>
          </div>
        </template>
        <template v-else>
          <textarea
            ref="textareaRef"
            v-model="promptDraft"
            class="ne-prompt-input"
            :placeholder="promptPlaceholder"
            @keydown.ctrl.enter="onSubmit"
            @keydown.meta.enter="onSubmit"
          ></textarea>
          <div class="ne-status-text">
            {{ statusText }}
          </div>
        </template>
      </div>

      <!-- 文本节点：横向控件栏 -->
      <div v-if="nodeType === 'text'" class="ne-controls">
        <!-- 模型按钮 -->
        <div class="ne-model-wrap">
          <button
            :ref="el => setMenuBtnRef('model', el)"
            class="ne-ctrl-btn ne-ctrl-model"
            :class="{ 'is-active': openMenuKey === 'model' }"
            type="button"
            @click="toggleMenu('model')"
          >
            <svg class="ne-model-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3l1.6 4.6L18 9.2l-4.4 1.6L12 15l-1.6-4.2L6 9.2l4.4-1.6L12 3z" />
              <path d="M19 14l.8 2.2L22 17l-2.2.8L19 20l-.8-2.2L16 17l2.2-.8L19 14z" />
            </svg>
            <span class="ne-model-name" :class="{ 'is-placeholder': !modelName }">{{ modelName || modelPlaceholder }}</span>
            <svg class="ne-model-caret" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
          </button>
        </div>

        <button class="ne-send-btn" type="button" :disabled="!canSubmit" @click="onSubmit">
          <span>{{ sendCount }}</span>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="m5 12 7-7 7 7" /><path d="M12 19V5" />
          </svg>
        </button>
      </div>

      <!-- 图片节点：横向下拉选择栏（与视频节点风格一致） -->
      <div v-else-if="nodeType === 'image'" class="ne-video-controls">
        <button
          v-for="key in ['model', 'ratio', 'imageStyle', 'resolution', 'count']"
          :key="key"
          :ref="el => setMenuBtnRef(key, el)"
          class="ne-vs-select ne-vs-model"
          :class="[`ne-vs-key-${key}`, { 'is-active': openMenuKey === key }]"
          type="button"
          :title="MENU_META[key].title"
          @click="toggleMenu(key)"
        >
          <span class="ne-vs-value" :class="{ 'is-placeholder': !getMenuValue(key) }">
            {{ getMenuLabel(key) || (key === 'model' ? '选择模型' : MENU_META[key].title) }}
          </span>
          <svg class="ne-vs-caret" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
        </button>

        <button class="ne-submit-circle" type="button" :disabled="!canSubmit || submitting" :title="submitting ? '生成中…' : '生成图片'" @click="onSubmit">
          <span v-if="submitting" class="ne-submit-loading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <span class="ne-submit-loading-text">生成中</span>
          </span>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="m5 12 7-7 7 7" /><path d="M12 19V5" />
          </svg>
        </button>
      </div>

      <!-- 音频节点：仅保留上传按钮的控件栏 -->
      <div v-else-if="isAudioNode" class="ne-audio-controls">
        <button class="ne-audio-ctrl-upload" type="button" :disabled="uploading" @click="onUploadClick">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>{{ uploading ? '上传中…' : '上传音频' }}</span>
        </button>
        <span class="ne-audio-ctrl-hint">暂不支持生成，仅上传音色文件</span>
      </div>

      <!-- 视频节点：横向下拉选择栏 -->
      <div v-else-if="isVideoNode" class="ne-video-controls">
        <button
          v-for="key in ['model', 'videoRatio', 'videoDuration', 'videoResolution', 'videoReferenceMode']"
          :key="key"
          :ref="el => setMenuBtnRef(key, el)"
          class="ne-vs-select ne-vs-model"
          :class="[`ne-vs-key-${key}`, { 'is-active': openMenuKey === key }]"
          type="button"
          :title="MENU_META[key].title"
          @click="toggleMenu(key)"
        >
          <span class="ne-vs-value" :class="{ 'is-placeholder': !getMenuValue(key) }">
            {{ getMenuLabel(key) || (key === 'model' ? '选择模型' : MENU_META[key].title) }}
          </span>
          <svg class="ne-vs-caret" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
        </button>

        <button class="ne-submit-circle" type="button" :disabled="!canSubmit || submitting" :title="submitting ? '生成中…' : '生成视频'" @click="onSubmit">
          <span v-if="submitting" class="ne-submit-loading">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <span class="ne-submit-loading-text">生成中</span>
          </span>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="m5 12 7-7 7 7" /><path d="M12 19V5" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 角色资产节点：音色设置 -->
    <div v-if="isCharacterAssetNode" class="ne-voice-wrap">
      <VoiceSettings
        :character-id="characterId"
        :character-name="characterName"
        :custom-voice-url="characterVoiceUrl"
        :compact="true"
        :upload-handler="props.voiceUploadHandler"
        @voice-select="onVoiceSelect"
      />
    </div>

    <Teleport to="body">
      <Transition name="ne-preview-fade">
        <div
          v-if="previewVisible && outputUrl"
          class="ne-fullscreen-overlay"
          @click.self="closePreview"
        >
          <button class="ne-fullscreen-close" type="button" title="关闭（Esc）" @click="closePreview">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">
              <path d="M18 6 6 18" /><path d="m6 6 12 12" />
            </svg>
          </button>
          <img
            v-if="isImageNode"
            :src="outputUrl"
            class="ne-fullscreen-media"
            alt=""
            @click.stop
          />
          <video
            v-else
            :src="outputUrl"
            class="ne-fullscreen-media"
            controls
            autoplay
            @click.stop
          />
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="openMenuKey"
        class="ne-model-menu"
        :style="menuStyle"
        @click.stop
        @mousedown.stop
      >
        <div class="ne-mm-header">
          <span>{{ MENU_META[openMenuKey].title }}</span>
          <span v-if="openMenuKey === 'model' && modelLoading" class="ne-mm-loading">加载中</span>
        </div>
        <div v-if="openMenuKey === 'model' && !modelLoading && modelOptions.length === 0" class="ne-mm-empty">
          暂无可用模型<br/>请先在配置中心添加
        </div>
        <div v-else-if="openMenuKey === 'model' && modelLoading" class="ne-mm-empty">加载中…</div>
        <div v-else class="ne-mm-list">
          <button
            v-for="opt in getMenuOptions(openMenuKey)"
            :key="opt.value"
            class="ne-mm-item"
            :class="{ 'is-selected': opt.value === getMenuValue(openMenuKey) }"
            type="button"
            @click.stop="onSelectMenu(openMenuKey, opt)"
          >
            <div class="ne-mm-item-body">
              <span class="ne-mm-name">{{ opt.label }}</span>
              <span v-if="opt.provider" class="ne-mm-provider">{{ opt.provider }}</span>
            </div>
            <svg class="ne-mm-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </button>
        </div>
      </div>
    </Teleport>

    <input
      ref="fileInputRef"
      class="ne-file-input"
      type="file"
      :accept="fileAccept"
      @change="onFileChange"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { getModelOptions } from '@/api/aiModel'
import { registerCanvasAsset } from '@/api/canvas'
import { uploadCanvasAssetDirect } from '@/views/Canvas/utils/mediaUpload'
import { useUserStore } from '@/store/user'
import { isHeicFile, convertHeicToJpegFile } from '@/utils/cosUpload'
import CanvasBodyEditor from './CanvasBodyEditor.vue'
import PromptMentionEditor from './PromptMentionEditor.vue'
import VoiceSettings from '@/views/AssetsCenter/components/VoiceSettings.vue'

const props = defineProps({
  nodeData: { type: Object, required: true },
  saving: { type: Boolean, default: false },
  availableNodes: { type: Array, default: () => [] },
  // 入连线上游节点（含组展开后的子节点），用于驱动预览区缩略图
  incomingUpstreamNodes: { type: Array, default: () => [] },
  viewportTick: { type: Number, default: 0 },
  voiceUploadHandler: { type: Function, default: null },
})

const emit = defineEmits(['close', 'save', 'side-add', 'submit', 'focus-item', 'open-history', 'open-asset-picker', 'imported', 'delete', 'open-voice-picker', 'unlink-reference'])

const TYPE_LABELS = { text: '文本', image: '图片', video: '视频', audio: '音频' }
const ROLE_LABEL = { first_frame: '首', last_frame: '尾', reference: '参' }
const RESOLUTION_OPTS = [
  { value: '1K', label: '1K' },
  { value: '2K', label: '2K' },
]
const RATIO_OPTS = [
  { value: '16:9', label: '16:9' },
  { value: '9:16', label: '9:16' },
  { value: '1:1', label: '1:1' },
  { value: '4:3', label: '4:3' },
  { value: '3:4', label: '3:4' },
  { value: '21:9', label: '21:9' },
]
const IMAGE_STYLE_OPTS = [
  { value: 'american-comic', label: '漫画风' },
  { value: 'chinese-comic', label: '精致国漫' },
  { value: 'japanese-anime', label: '日系动漫风' },
  { value: 'realistic', label: '真人风格' },
  // 自定义：不注入任何预设风格指令，完全由用户 prompt 自由控制画风（等价于"不限制风格"）
  { value: 'custom', label: '自定义' },
]
const IMAGE_COUNT_OPTS = [
  { value: 1, label: '1 张' },
  { value: 2, label: '2 张' },
  { value: 3, label: '3 张' },
  { value: 4, label: '4 张' },
]
const VIDEO_RATIO_OPTS = [
  { value: '16:9', label: '16:9' },
  { value: '9:16', label: '9:16' },
  { value: '1:1', label: '1:1' },
  { value: '4:3', label: '4:3' },
  { value: '3:4', label: '3:4' },
  { value: '21:9', label: '21:9' },
  { value: 'adaptive', label: '自适应' },
]
const VIDEO_DURATION_OPTS = Array.from({ length: 12 }, (_, i) => ({
  value: i + 4,
  label: `${i + 4}s`,
}))
const VIDEO_RESOLUTION_OPTS = [
  { value: '480p', label: '480P' },
  { value: '720p', label: '720P' },
  { value: '1080p', label: '1080P' },
]
const VIDEO_REFERENCE_MODE_OPTS = [
  { value: 'reference', label: '参考生成' },
  { value: 'first_last_frame', label: '首尾帧' },
]
// 视频模型按区域固定展示（与短视频页一致）：
// 国内：Seedance 2.0 / Seedance 2.0 Fast；国际：Dreamina Seedance 2.0
const REGION_VIDEO_MODEL_OPTIONS = {
  domestic: [
    { model_name: 'doubao-seedance-2-0-260128', name: 'Seedance 2.0', provider_name: '火山引擎' },
    { model_name: 'doubao-seedance-2-0-fast-260128', name: 'Seedance 2.0 Fast', provider_name: '火山引擎' },
  ],
  overseas: [
    { model_name: 'dreamina-seedance-2-0-260128', name: 'Dreamina Seedance 2.0', provider_name: 'BytePlus' },
  ],
}

const userStore = useUserStore()
const currentRegion = computed(() => userStore.userInfo.value?.region || 'domestic')

// unmount 期间 props.nodeData 可能已被父组件置空，但 doSave 还要靠 nodeType 决定走哪个分支
// （视频节点要带 prompt_tokens、文本节点要带 body），fallback 到 lastItemType 保证类型判断正确
const nodeType = computed(() => props.nodeData?.item_type || lastItemType.value || 'text')
const typeLabel = computed(() => TYPE_LABELS[nodeType.value] || '节点')
const isTextNode = computed(() => nodeType.value === 'text')
const isVideoNode = computed(() => nodeType.value === 'video')
const isImageNode = computed(() => nodeType.value === 'image')
const isAudioNode = computed(() => nodeType.value === 'audio')
const isCharacterAssetNode = computed(
  () => isImageNode.value && props.nodeData?.asset_tag === 'character'
)
const characterVoiceUrl = computed(() => props.nodeData?.voice_url || null)
const characterId = computed(() => props.nodeData?.id || '')
const characterName = computed(() => props.nodeData?.title || '角色')

function onVoiceSelect() {
  emit('open-voice-picker', { id: characterId.value })
}
const modelPlaceholder = computed(() => {
  if (nodeType.value === 'text') return '选择文本模型'
  if (nodeType.value === 'image') return '选择图片模型'
  if (nodeType.value === 'audio') return '上传音频文件'
  return '选择视频模型'
})
const promptPlaceholder = computed(() => {
  if (nodeType.value === 'text') return '输入 prompt 生成正文…'
  if (nodeType.value === 'image') return '描述任何你想要生成的内容'
  if (nodeType.value === 'audio') return '音频节点暂不支持 prompt，请直接上传文件'
  return '描述你想要的视频内容...'
})
const bodyPlaceholder = computed(() => '编辑正文（Ctrl+B 加粗，Ctrl+I 斜体）')

const promptDraft = ref('')
const bodyHtml = ref('')
const promptTokens = ref([])

// 按当前模式 + 图片位置推导角色：首尾帧模式下第 1 张=首、第 2 张=尾、其余=参；
// 参考生成模式下全部=参。token 里存的 role 可能滞后（新建 chip 默认 reference），
// 这里统一算出"当前应有的角色"，display / save 都用它。
const effectivePromptTokens = computed(() => {
  const tokens = promptTokens.value
  if (!isVideoNode.value) return tokens
  const mode = params.value.videoReferenceMode
  let imageCount = 0
  let changed = false
  const next = tokens.map(t => {
    if (t.type !== 'mention' || t.node_type !== 'image') return t
    imageCount += 1
    let expected = t.role
    if (mode === 'reference') {
      expected = 'reference'
    } else if (mode === 'first_last_frame') {
      expected = imageCount === 1 ? 'first_frame'
        : imageCount === 2 ? 'last_frame'
        : 'reference'
    }
    if (t.role !== expected) {
      changed = true
      return { ...t, role: expected }
    }
    return t
  })
  return changed ? next : tokens
})

const promptPlainText = computed(() => {
  return effectivePromptTokens.value.map(t => {
    if (t.type === 'mention') {
      const role = t.node_type === 'image' && t.role ? `#${t.role}` : ''
      return `[${t.node_title || t.node_id || '节点'}${role}]`
    }
    return t.value || ''
  }).join('')
})

// 预览区缩略图：基于入连线上游节点（incomingUpstreamNodes，组已展开），不再依赖 prompt_tokens。
// 角色（首/尾/参）仍从 prompt_tokens 中查（用户可手动 @ 加 role 标注）。
const referencedNodes = computed(() => {
  const tokens = effectivePromptTokens.value || []
  // 按 node_id 保留首条 role 标注（手动 @ 的 role 优先级最高）
  const roleByNodeId = new Map()
  for (const t of tokens) {
    if (t.type === 'mention' && t.role && !roleByNodeId.has(t.node_id)) {
      roleByNodeId.set(t.node_id, t.role)
    }
  }
  const result = []
  let imageIdx = 0
  let videoIdx = 0
  let audioIdx = 0
  const occurrenceByNode = {}
  ;(props.incomingUpstreamNodes || []).forEach((node, idx) => {
    const nodeType = (node.item_type || '').toLowerCase()
    const isImage = nodeType === 'image'
    const isVideo = nodeType === 'video'
    const isAudio = nodeType === 'audio'
    if (isImage) imageIdx += 1
    if (isVideo) videoIdx += 1
    if (isAudio) audioIdx += 1
    const occ = occurrenceByNode[node.id] || 0
    occurrenceByNode[node.id] = occ + 1
    result.push({
      ...node,
      node_type: nodeType,
      tokenIdx: idx,
      tokenKey: `${node.id}-${occ}`,
      role: roleByNodeId.get(node.id) || 'reference',
      previewText: node.previewText || node.title || '(无内容)',
      imageIdx: isImage ? imageIdx : null,
      videoIdx: isVideo ? videoIdx : null,
      audioIdx: isAudio ? audioIdx : null,
    })
  })
  return result
})

const showSwapButton = computed(() => {
  if (!isVideoNode.value) return false
  if (params.value.videoReferenceMode !== 'first_last_frame') return false
  return referencedNodes.value.filter((r) => r.node_type === 'image').length >= 2
})

function showRoleFor(ref) {
  if (!ref.role) return false
  if (isVideoNode.value) {
    return params.value.videoReferenceMode === 'first_last_frame' && ref.node_type === 'image'
  }
  if (isImageNode.value) return false
  return true
}

async function swapFirstLastFrames() {
  if (swappingLock.value) return
  swappingLock.value = true
  try {
    const tokens = promptTokens.value.map((t) => ({ ...t }))
    const imageIdxs = []
    tokens.forEach((t, idx) => {
      if (t.type === 'mention' && t.node_type === 'image') imageIdxs.push(idx)
    })
    if (imageIdxs.length >= 2) {
      const i1 = imageIdxs[0]
      const i2 = imageIdxs[1]
      const tmp = tokens[i1]
      tokens[i1] = tokens[i2]
      tokens[i2] = tmp
      promptTokens.value = tokens
    }
    await nextTick()
    setTimeout(() => { swappingLock.value = false }, 120)
  } catch (e) {
    swappingLock.value = false
    throw e
  }
}

const canSubmit = computed(() => {
  if (isVideoNode.value) {
    // 视频节点必须输入文本描述（仅挂图片引用不允许提交）
    return promptTokens.value.some(t =>
      t.type === 'text' && (t.value || '').trim().length > 0
    )
  }
  if (isTextNode.value || isImageNode.value) {
    return promptTokens.value.some(t =>
      t.type === 'mention' || (t.value || '').trim().length > 0
    )
  }
  return promptDraft.value.trim().length > 0
})
const params = ref({
  resolution: '1K',
  ratio: '16:9',
  imageStyle: 'custom',
  videoRatio: '16:9',
  videoResolution: '720p',
  videoDuration: 5,
  videoReferenceMode: 'reference',
  count: 1,
  videoCount: 1,
})
// 模型选择保存在本地状态，统一通过 doSave 与其他字段一起下发
// 避免直接 emit('save') 用旧 content_json 覆盖本地未保存的 prompt
const localModel = ref({
  model_name: '',
  model_display_name: '',
  provider_name: '',
})
const sendCount = ref(1)
const submitting = ref(false)
const textareaRef = ref(null)
const videoPromptEditorRef = ref(null)
const imagePromptEditorRef = ref(null)
const panelRootRef = ref(null)
const swappingLock = ref(false)
const titleDraft = ref('')
const titleInputRef = ref(null)

// 通用下拉菜单（模型 / 视频各参数）
const modelOptions = ref([])
const modelLoading = ref(false)
const openMenuKey = ref(null) // null | 'model' | 'videoRatio' | ... | 'ratio' | 'imageStyle' | 'resolution' | 'count'
const menuStyle = ref({})
const menuBtnRefs = {}
const MENU_META = {
  model: { title: '选择模型', width: 240 },
  // 图片节点
  ratio: { title: '画面比例', width: 120 },
  imageStyle: { title: '风格', width: 160 },
  resolution: { title: '分辨率', width: 120 },
  count: { title: '生成张数', width: 120 },
  // 视频节点
  videoRatio: { title: '画面比例', width: 120 },
  videoDuration: { title: '时长', width: 120 },
  videoResolution: { title: '分辨率', width: 120 },
  videoReferenceMode: { title: '参考模式', width: 200 },
}

function setMenuBtnRef(key, el) {
  if (el) menuBtnRefs[key] = el
  else delete menuBtnRefs[key]
}

// 全屏原图预览
const previewVisible = ref(false)
function openPreview() {
  previewVisible.value = true
}
function closePreview() {
  previewVisible.value = false
}

function modelTypeFor(nt) {
  // 文本节点用 text，图片用 image，视频用 video
  return nt === 'text' ? 'text' : nt === 'image' ? 'image' : 'video'
}

async function loadModelOptions() {
  // 视频模型按区域固定，不走 API（避免依赖后端配置且确保与短视频页一致）
  const triggerItemId = props.nodeData?.id
  if (nodeType.value === 'video') {
    modelOptions.value = REGION_VIDEO_MODEL_OPTIONS[currentRegion.value] || []
    // 加载完成前若用户已切换节点，放弃默认选中（避免污染新节点的 localModel）
    if (props.nodeData?.id === triggerItemId) ensureDefaultModel()
    return
  }
  modelLoading.value = true
  try {
    // 仅返回当前用户已启用且配置了 API Key 的模型（避免选到无法调用的模型）
    const list = await getModelOptions(modelTypeFor(nodeType.value), null, { availableOnly: true })
    modelOptions.value = Array.isArray(list) ? list : (list?.data || [])
    if (props.nodeData?.id === triggerItemId) ensureDefaultModel()
  } catch (e) {
    modelOptions.value = []
  } finally {
    modelLoading.value = false
  }
}

// 图片/视频节点：若节点未选模型，默认选中列表中的第一个（写入本地状态，由 doSave 统一下发）
function ensureDefaultModel() {
  if (localModel.value.model_name) return
  const first = modelOptions.value[0]
  if (!first) return
  localModel.value = {
    model_name: first.model_name,
    model_display_name: first.name,
    provider_name: first.provider_name,
  }
}

function getMenuOptions(key) {
  if (key === 'model') {
    return modelOptions.value.map(o => ({ value: o.model_name, label: o.name, provider: o.provider_name, raw: o }))
  }
  // 图片节点
  if (key === 'ratio') return RATIO_OPTS
  if (key === 'imageStyle') return IMAGE_STYLE_OPTS
  if (key === 'resolution') return RESOLUTION_OPTS
  if (key === 'count') return IMAGE_COUNT_OPTS
  // 视频节点
  if (key === 'videoRatio') return VIDEO_RATIO_OPTS
  if (key === 'videoDuration') return VIDEO_DURATION_OPTS
  if (key === 'videoResolution') return VIDEO_RESOLUTION_OPTS
  if (key === 'videoReferenceMode') return VIDEO_REFERENCE_MODE_OPTS
  return []
}

function getMenuValue(key) {
  if (key === 'model') return modelValue.value
  return params.value[key]
}

function getMenuLabel(key) {
  const value = getMenuValue(key)
  const opts = getMenuOptions(key)
  const found = opts.find(o => o.value === value)
  return found?.label || ''
}

function estimateMenuHeight(key) {
  const opts = getMenuOptions(key)
  // 模型项含 provider 子标题，单行更高
  const itemHeight = key === 'model' ? 52 : 40
  return Math.min(320, Math.max(96, opts.length * itemHeight + 44))
}

function toggleMenu(key) {
  if (openMenuKey.value === key) {
    closeMenu()
    return
  }
  if (key === 'model' && modelOptions.value.length === 0) {
    loadModelOptions()
  }
  const el = menuBtnRefs[key]
  if (el) {
    const rect = el.getBoundingClientRect()
    const MENU_WIDTH = MENU_META[key].width
    const estimatedHeight = estimateMenuHeight(key)
    let left = rect.left
    if (left + MENU_WIDTH > window.innerWidth - 8) left = window.innerWidth - MENU_WIDTH - 8
    let top = rect.bottom + 4
    if (top + estimatedHeight > window.innerHeight - 8) {
      top = Math.max(8, rect.top - estimatedHeight - 4)
    }
    menuStyle.value = {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
      width: `${MENU_WIDTH}px`,
      zIndex: 1001,
    }
  }
  openMenuKey.value = key
}

function closeMenu() {
  openMenuKey.value = null
}

function inferVideoReferenceMode(tokens) {
  const imageTokens = (tokens || []).filter(t => t.type === 'mention' && t.node_type === 'image')
  if (!imageTokens.length) return null
  const hasFrameRole = imageTokens.some(t => t.role === 'first_frame' || t.role === 'last_frame')
  return hasFrameRole ? 'first_last_frame' : 'reference'
}

function onSelectMenu(key, opt) {
  if (key === 'model') {
    const raw = opt.raw || modelOptions.value.find(o => o.model_name === opt.value)
    if (raw) {
      // 仅修改本地状态，由 watch 触发 scheduleSave → doSave 统一下发
      // 避免直接 emit save 用旧 content_json 覆盖未保存的 prompt
      localModel.value = {
        model_name: raw.model_name,
        model_display_name: raw.name,
        provider_name: raw.provider_name,
      }
      closeMenu()
    }
    return
  }
  if (key === 'videoReferenceMode') {
    // 切换模式时不直接改 tokens：role 由 effectivePromptTokens 按位置实时推导
    params.value.videoReferenceMode = opt.value
    closeMenu()
    return
  }
  if (key === 'videoDuration' || key === 'count') {
    params.value[key] = Number(opt.value)
  } else {
    params.value[key] = opt.value
  }
  closeMenu()
}

function onDocClickCloseMenu(e) {
  if (!openMenuKey.value) return
  if (e.target.closest('.ne-model-menu')) return
  if (e.target.closest('.ne-vs-select')) return
  closeMenu()
}

// 编辑弹框内部的点击：点空白处时收起已展开的下拉菜单
// （editor-popover 有 @click.stop 阻止冒泡，document 监听收不到，所以在面板内自处理）
function onPanelClickCloseMenu(e) {
  if (!openMenuKey.value) return
  if (e.target.closest('.ne-vs-select')) return
  closeMenu()
}

function onKeydownCloseMenu(e) {
  if (e.key === 'Escape') closeMenu()
}

// 任意滚动（弹框内部 / 画布 / window）时，让浮层跟随按钮新位置；按钮滚出视口则关闭
function onAnyScrollUpdateMenu() {
  if (!openMenuKey.value) return
  const key = openMenuKey.value
  const el = menuBtnRefs[key]
  if (!el) {
    closeMenu()
    return
  }
  const rect = el.getBoundingClientRect()
  // 按钮完全离开视口：关菜单
  if (rect.bottom < 0 || rect.top > window.innerHeight || rect.right < 0 || rect.left > window.innerWidth) {
    closeMenu()
    return
  }
  const MENU_WIDTH = MENU_META[key].width
  const estimatedHeight = estimateMenuHeight(key)
  let left = rect.left
  if (left + MENU_WIDTH > window.innerWidth - 8) left = window.innerWidth - MENU_WIDTH - 8
  let top = rect.bottom + 4
  if (top + estimatedHeight > window.innerHeight - 8) {
    top = Math.max(8, rect.top - estimatedHeight - 4)
  }
  menuStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    width: `${MENU_WIDTH}px`,
    zIndex: 1001,
  }
}

// 画布平移/缩放（viewport 变化）：浮层是 fixed 定位，无法稳定跟随弹框，
// 直接关闭，避免错位（element-plus 等组件库在 popper 滚动时的通用做法）
watch(
  () => props.viewportTick,
  () => {
    if (openMenuKey.value) closeMenu()
  }
)

const modelName = computed(() => localModel.value.model_display_name || localModel.value.model_name || '')
// 用于下拉匹配的值（model_name），与 getMenuOptions 返回的 opt.value 对齐
const modelValue = computed(() => localModel.value.model_name || '')
const outputUrl = computed(() => props.nodeData?.last_output_json?.url || '')
const audioName = computed(() => props.nodeData?.last_output_json?.filename || props.nodeData?.content_json?.filename || '')
const statusBadgeText = computed(() => (nodeType.value === 'video' ? '已生成' : '已生成'))

const statusText = computed(() => {
  return '将根据 prompt 和参考图生成。'
})

let lastSavedSnapshot = ''
// 最近一次通过 emit('save') 下发的 snapshot；用于判断 nodeData 回写时本地是否有更新未发的内容
let lastEmittedSnapshot = ''

// 缓存最后有效的 itemId / item_type：unmount 触发 onBeforeUnmount 时，
// 父组件可能已经把 nodeData 置空（如 closeEditor 把 editingNodeId 设为 null 后 v-if 卸载），
// 此时 props.nodeData 是 null，doSave 仍需基于缓存判断节点类型、emit 正确的 itemId。
const lastItemId = ref('')
const lastItemType = ref('text')

// 防抖保存定时器句柄。必须在 watch(nodeData)（immediate）之前声明：
// 该 watch 的回调在节点切换时会引用 saveTimer，若声明在后面会触发 TDZ（ReferenceError）。
let saveTimer = null

// 用 nodeData 把本地编辑状态重置一次（用于节点切换或确认本地无未保存改动时同步远端）
function resetLocalFromData(val) {
  const cj = val.content_json || {}
  // 标题输入框必须随 nodeData.title 同步，否则切换节点或外部回写后输入框会停留在旧值/空值
  titleDraft.value = val.title || ''
  promptDraft.value = cj.prompt || ''
  bodyHtml.value = cj.body || cj.text || ''
  promptTokens.value = Array.isArray(cj.prompt_tokens) ? cj.prompt_tokens.map(t => ({ ...t })) : []
  params.value = {
    resolution: cj.resolution || '1K',
    ratio: cj.ratio || '16:9',
    imageStyle: cj.image_style || 'custom',
    videoRatio: cj.video_ratio || '16:9',
    videoResolution: cj.video_resolution || '720p',
    videoDuration: cj.video_duration || 5,
    videoReferenceMode: cj.video_reference_mode || 'reference',
    count: cj.count || 1,
    videoCount: cj.video_count || 1,
  }
  localModel.value = {
    model_name: cj.model_name || '',
    model_display_name: cj.model_display_name || '',
    provider_name: cj.provider_name || '',
  }
}

watch(
  () => props.nodeData,
  (val, oldVal) => {
    if (!val) return
    // 缓存最后有效的节点信息，供 unmount 时的 doSave 使用
    if (val.id) lastItemId.value = val.id
    if (val.item_type) lastItemType.value = val.item_type
    const isNodeSwitch = val?.id !== oldVal?.id
    if (isNodeSwitch) {
      // 切换节点前，先把上一个节点未落库的输入 flush 掉，避免快速切换时丢失内容。
      // 注意：只在真正切换（oldVal 有效）时 flush。本 watch 是 immediate，组件挂载首次
      // 触发时 oldVal=undefined、本地草稿还是初始空值，若此时 doSave 会把空内容存进
      // 新打开的节点、覆盖其原有内容（表现为"重新打开节点变空白"）。
      if (oldVal && oldVal.id) {
        if (saveTimer) {
          clearTimeout(saveTimer)
          saveTimer = null
        }
        // 必须在 resetLocalFromData 之前 flush：此时本地草稿仍是旧节点 oldVal 的值
        doSave(oldVal)
      }
      // 切换节点：完全重置本地状态
      resetLocalFromData(val)
      lastSavedSnapshot = buildSnapshot()
      lastEmittedSnapshot = lastSavedSnapshot
    } else {
      // 同节点内容变化（多为本组件 doSave 触发的回写、或 WS/生成完成推送）
      // 仅当本地没有比上次 emit 更新的内容时，才同步远端，避免覆盖用户在保存过程中继续输入的内容
      const currentSnap = buildSnapshot()
      if (currentSnap === lastEmittedSnapshot) {
        resetLocalFromData(val)
        lastSavedSnapshot = buildSnapshot()
        lastEmittedSnapshot = lastSavedSnapshot
      }
    }
    // 切换节点或节点类型变化时，关闭菜单并清空已加载模型（让下次打开时按新类型重载）
    if (val?.item_type !== oldVal?.item_type) {
      modelOptions.value = []
    }
    // 图片/视频节点：确保模型列表已加载，并在未选模型时默认选中第一个
    if (val.item_type === 'image' || val.item_type === 'video') {
      if (modelOptions.value.length === 0) {
        loadModelOptions()
      } else {
        ensureDefaultModel()
      }
    }
    closeMenu()
    nextTick(() => {
      textareaRef.value?.focus()
    })
  },
  { immediate: true, deep: false }
)

function buildSnapshot() {
  return JSON.stringify({
    prompt: promptDraft.value,
    bodyHtml: bodyHtml.value,
    promptTokens: promptTokens.value,
    params: params.value,
    model: localModel.value,
  })
}

watch([promptDraft, bodyHtml, promptTokens, params, localModel], () => {
  const snap = buildSnapshot()
  if (snap === lastSavedSnapshot) return
  scheduleSave()
}, { deep: true })

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    saveTimer = null
    doSave()
  }, 600)
}

// doSave 前主动 flush PromptMentionEditor 的 contenteditable DOM 到 promptTokens，
// 捕获 composing 中/未 emit 的输入（尤其中文输入法）。由父组件统一控制时机——不在子组件
// onBeforeUnmount 里 flush，以免跨节点类型切换（image↔video 用不同 editor 实例）时旧实例
// 卸载把旧内容 emit 回去，污染已 reset 的新节点 promptTokens（内容串台）。
function flushCurrentPromptEditor(itemType) {
  const editorRef = itemType === 'video' ? videoPromptEditorRef.value : imagePromptEditorRef.value
  editorRef?.flushTokens?.()
}

function doSave(overrideNodeData) {
  // overrideNodeData 用于节点切换 flush：此时本地草稿是旧节点的，但 props.nodeData 已是新节点，需用旧节点数据
  // unmount 触发 onBeforeUnmount 时父组件可能已把 nodeData 置空，
  // 用缓存兜底（lastItemId/lastItemType 在 watch nodeData 中持续更新）
  const nodeData = overrideNodeData || props.nodeData || {}
  const itemId = nodeData.id || lastItemId.value || ''
  const itemType = nodeData.item_type || lastItemType.value || 'text'
  // 先 flush 当前 editor 的 DOM，确保 composing/未 emit 的输入进入 promptTokens 再保存
  flushCurrentPromptEditor(itemType)
  const isText = itemType === 'text'
  const isVideo = itemType === 'video'
  const isImage = itemType === 'image'
  // 清掉 pending 的 scheduleSave：内容已 emit，不需要再次落库
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  const baseContent = {
    ...(nodeData.content_json || {}),
    resolution: params.value.resolution,
    ratio: params.value.ratio,
    image_style: params.value.imageStyle,
    video_ratio: params.value.videoRatio,
    video_resolution: params.value.videoResolution,
    video_duration: params.value.videoDuration,
    video_reference_mode: params.value.videoReferenceMode,
    count: params.value.count,
    video_count: params.value.videoCount,
  }
  // 合并本地模型字段（图片/视频节点）
  if (localModel.value.model_name) {
    baseContent.model_name = localModel.value.model_name
    baseContent.model_display_name = localModel.value.model_display_name
    baseContent.provider_name = localModel.value.provider_name
  }
  if (isText) {
    baseContent.body = bodyHtml.value
    baseContent.prompt = promptDraft.value
  } else if (isVideo || isImage) {
    baseContent.prompt_tokens = effectivePromptTokens.value
    baseContent.prompt_plain_text = promptPlainText.value
    baseContent.prompt = promptPlainText.value
  } else {
    baseContent.prompt = promptDraft.value
  }
  const payload = {
    title: (titleDraft.value || '').trim() || null,
    content_json: baseContent,
    generation_config_json: {
      ...(nodeData.generation_config_json || {}),
    },
  }
  lastSavedSnapshot = buildSnapshot()
  lastEmittedSnapshot = lastSavedSnapshot
  // 把 itemId 一起带给父组件：closeEditor/切换节点时父组件可能已经清空 editingNodeId，
  // 此时 onEditorSave 用 editingNodeId 会拿不到 id
  emit('save', payload, itemId)
}

function clearPrompt() {
  promptDraft.value = ''
  textareaRef.value?.focus()
}

function onTitleCommit() {
  const trimmed = (titleDraft.value || '').trim()
  titleDraft.value = trimmed
  const current = props.nodeData?.title || ''
  if (trimmed === current) return
  doSave()
}

function onTitleCancel() {
  titleDraft.value = props.nodeData?.title || ''
  titleInputRef.value?.blur()
}

function onSubmit() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  doSave()
  sendCount.value += 1
  // 把页面选择的模型随提交一并下发（生成时优先使用）；优先读 localModel，避免后端尚未回写
  const modelNameVal = localModel.value.model_name || props.nodeData?.content_json?.model_name || null
  try {
    if (isTextNode.value || isVideoNode.value || isImageNode.value) {
      emit('submit', {
        prompt_tokens: effectivePromptTokens.value,
        prompt_plain_text: promptPlainText.value,
        params: { ...params.value, model: modelNameVal },
      })
      return
    }
    emit('submit', {
      prompt: promptDraft.value,
      params: { ...params.value, model: modelNameVal },
    })
  } finally {
    // 提交后父组件通常会关闭面板；保留 1.5s 置灰避免面板关闭前的重复点击，
    // 也兜底父组件未关闭面板的场景
    setTimeout(() => { submitting.value = false }, 1500)
  }
}

function onFocusItem(nodeId) {
  // 点击 chip 时跳转到上游节点（由父组件实现）
  emit('focus-item', nodeId)
}

function removeReference(ref) {
  // 删除引用 = 断开"被引用节点(source) → 当前编辑节点(target)"的连线；
  // prompt_tokens 中对应 mention 的清理交给父组件 removeUpstreamReference 统一完成，
  // 避免本地与连线/后端状态双写不一致。
  if (!ref?.id) return
  emit('unlink-reference', ref.id)
}

// ── 资产导入（上传 / 资产中心） ───────────────────────
const fileInputRef = ref(null)
const uploading = ref(false)

const fileAccept = computed(() => {
  if (isImageNode.value) return '.jpeg,.jpg,.png,.webp,.bmp,.gif,.heic,.heif'
  if (isVideoNode.value) return '.mp4,.mov'
  if (isAudioNode.value) return 'audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,audio/aac,audio/flac'
  return ''
})

// 图片上传约束（与短视频页 EditorBar 一致）
const IMAGE_ALLOWED_EXTS = ['jpeg', 'jpg', 'png', 'webp', 'bmp', 'gif', 'heic', 'heif']
const IMAGE_MAX_SIZE = 30 * 1024 * 1024
const IMAGE_DIM_MIN = 300
const IMAGE_DIM_MAX = 6000
const IMAGE_RATIO_MIN = 0.4
const IMAGE_RATIO_MAX = 2.5
// 视频上传约束（与短视频页 EditorBar 一致）
const VIDEO_ALLOWED_EXTS = ['mp4', 'mov']
const VIDEO_MAX_SIZE = 50 * 1024 * 1024
const VIDEO_DIM_MIN = 300
const VIDEO_DIM_MAX = 6000
const VIDEO_RATIO_MIN = 0.4
const VIDEO_RATIO_MAX = 2.5
const VIDEO_PIXELS_MIN = 409600      // ≈ 640×640
const VIDEO_PIXELS_MAX = 2086876     // ≈ 1445×1445
const VIDEO_DURATION_MIN = 2
const VIDEO_DURATION_MAX = 15
const VIDEO_FILENAME_MAX_LEN = 64

function getExt(name) {
  const idx = (name || '').lastIndexOf('.')
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : ''
}

function readImageSize(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve({ w: img.naturalWidth, h: img.naturalHeight })
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(null)
    }
    img.src = url
  })
}

function readVideoMeta(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    const video = document.createElement('video')
    video.preload = 'metadata'
    video.muted = true
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url)
      resolve({
        w: video.videoWidth,
        h: video.videoHeight,
        duration: video.duration,
      })
    }
    video.onerror = () => {
      URL.revokeObjectURL(url)
      resolve(null)
    }
    video.src = url
  })
}

function onUploadClick() {
  if (uploading.value) return
  fileInputRef.value?.click()
}

async function onFileChange(e) {
  let file = e.target.files?.[0]
  e.target.value = ''  // 重置允许下次选同一文件
  if (!file) return
  const itemId = props.nodeData?.id
  if (!itemId) return

  // 图片节点：HEIC/HEIF 先转 JPEG（与短视频页一致；浏览器无法预览/读尺寸）
  if (isImageNode.value && isHeicFile(file)) {
    uploading.value = true
    try {
      file = await convertHeicToJpegFile(file)
    } catch (err) {
      ElMessage.error('HEIC 文件解码失败，请尝试转换为 JPEG 后再上传')
      return
    } finally {
      uploading.value = false
    }
  }

  // 格式校验
  if (isImageNode.value) {
    const ext = getExt(file.name)
    if (!IMAGE_ALLOWED_EXTS.includes(ext)) {
      ElMessage.error('不支持的图片格式，请上传 jpeg/jpg/png/webp/bmp/gif/heic/heif')
      return
    }
    if (file.size > IMAGE_MAX_SIZE) {
      ElMessage.error('图片大小不能超过 30MB')
      return
    }
    // 尺寸 / 比例校（HEIC 已转 JPEG，可正常解码）
    const size = await readImageSize(file)
    if (!size) {
      ElMessage.error('无法解析图片尺寸，可能不是有效图片')
      return
    }
    if (size.w < IMAGE_DIM_MIN || size.w > IMAGE_DIM_MAX || size.h < IMAGE_DIM_MIN || size.h > IMAGE_DIM_MAX) {
      ElMessage.error(`图片尺寸需在 ${IMAGE_DIM_MIN}-${IMAGE_DIM_MAX}px 之间（当前 ${size.w}×${size.h}）`)
      return
    }
    const ratio = size.w / size.h
    if (ratio < IMAGE_RATIO_MIN || ratio > IMAGE_RATIO_MAX) {
      ElMessage.error(`图片宽高比需在 ${IMAGE_RATIO_MIN}-${IMAGE_RATIO_MAX} 之间（当前 ${ratio.toFixed(2)}）`)
      return
    }
  } else if (isVideoNode.value) {
    const ext = getExt(file.name)
    if (!VIDEO_ALLOWED_EXTS.includes(ext)) {
      ElMessage.error('不支持的视频格式，请上传 mp4 / mov')
      return
    }
    if (file.size > VIDEO_MAX_SIZE) {
      ElMessage.error('视频大小不能超过 50MB')
      return
    }
    if ((file.name || '').length > VIDEO_FILENAME_MAX_LEN) {
      ElMessage.error(`视频文件名过长（超过 ${VIDEO_FILENAME_MAX_LEN} 个字符），请重命名后再上传`)
      return
    }
    // 时长 / 分辨率 / 比例 / 像素总数（与短视频页一致）
    const meta = await readVideoMeta(file)
    if (!meta || !meta.w || !meta.h) {
      ElMessage.error('无法读取视频信息，请检查文件是否损坏')
      return
    }
    const roundedDuration = meta.duration != null ? Math.round(meta.duration) : null
    if (roundedDuration != null && (roundedDuration < VIDEO_DURATION_MIN || roundedDuration > VIDEO_DURATION_MAX)) {
      ElMessage.error(`视频时长需在 ${VIDEO_DURATION_MIN}-${VIDEO_DURATION_MAX} 秒之间（当前 ${roundedDuration} 秒）`)
      return
    }
    if (meta.w < VIDEO_DIM_MIN || meta.w > VIDEO_DIM_MAX || meta.h < VIDEO_DIM_MIN || meta.h > VIDEO_DIM_MAX) {
      ElMessage.error(`视频分辨率需在 ${VIDEO_DIM_MIN}-${VIDEO_DIM_MAX}px 之间（当前 ${meta.w}×${meta.h}）`)
      return
    }
    const ratio = meta.w / meta.h
    if (ratio < VIDEO_RATIO_MIN || ratio > VIDEO_RATIO_MAX) {
      ElMessage.error(`视频宽高比需在 ${VIDEO_RATIO_MIN}-${VIDEO_RATIO_MAX} 之间（当前 ${ratio.toFixed(2)}）`)
      return
    }
    const pixels = meta.w * meta.h
    if (pixels < VIDEO_PIXELS_MIN || pixels > VIDEO_PIXELS_MAX) {
      ElMessage.error(`视频像素总数需在 ${VIDEO_PIXELS_MIN}-${VIDEO_PIXELS_MAX} 之间（当前 ${pixels}）`)
      return
    }
  }

  uploading.value = true
  try {
    const resp = await uploadCanvasAssetDirect(itemId, file, nodeType.value)
    const updatedItem = resp?.item || null
    ElMessage.success(isImageNode.value ? '图片已导入' : isAudioNode.value ? '音频已导入' : '视频已导入')
    if (updatedItem) emit('imported', updatedItem)
  } catch (err) {
    ElMessage.error(err?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    if (previewVisible.value) {
      closePreview()
      return
    }
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('keydown', onKeydownCloseMenu)
  document.addEventListener('click', onDocClickCloseMenu)
  // capture 模式：捕获所有滚动容器（弹框内 / 画布 / window）
  window.addEventListener('scroll', onAnyScrollUpdateMenu, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('keydown', onKeydownCloseMenu)
  document.removeEventListener('click', onDocClickCloseMenu)
  window.removeEventListener('scroll', onAnyScrollUpdateMenu, true)
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  // 关闭前若还有未落库的改动，立刻 flush 一次。doSave 内部会先 flush 当前 editor 的 DOM
  // 捕获 composing/未 emit 的输入，所以不能只看 saveTimer（watch 异步可能尚未设置），
  // 用快照比对兜底，有改动就 doSave。
  if (buildSnapshot() !== lastSavedSnapshot) doSave()
})

defineExpose({ doSave })
</script>

<style scoped>
.ne-panel {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 18px;
  color: #1f2a44;
  font-family: inherit;
  overflow: hidden;
  animation: neFadeIn 0.2s ease-out;
}

@keyframes neFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ── 顶部操作栏 ── */
.ne-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(34, 57, 98, 0.06);
  background: linear-gradient(180deg, #fafbfc 0%, #f5f7fa 100%);
}

.ne-topbar-left {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.ne-topbar-right {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.ne-type-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #2f7bff;
}
.ne-type-image .ne-type-dot { background: #16a34a; }
.ne-type-video .ne-type-dot { background: #9333ea; }
.ne-type-audio .ne-type-dot { background: #f59e0b; }

.ne-type-label {
  font-size: 13px;
  font-weight: 600;
  color: #1f2a44;
}

.ne-title-input {
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  color: #1f2a44;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 3px 6px;
  margin: 0;
  outline: none;
  min-width: 0;
  width: 160px;
  transition: border-color 0.12s ease, background 0.12s ease;
}

.ne-title-input::placeholder {
  color: #9ca3af;
  font-weight: 500;
}

.ne-title-input:hover {
  border-color: rgba(34, 57, 98, 0.12);
  background: rgba(248, 249, 250, 0.6);
}

.ne-title-input:focus {
  border-color: rgba(75, 120, 255, 0.4);
  background: #fff;
}

.ne-status-pill {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
  border-radius: 999px;
}

.ne-icon-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #52607a;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.ne-icon-btn:hover {
  background: rgba(34, 57, 98, 0.06);
  color: #1f2a44;
}

.ne-close-btn:hover {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

.ne-topbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 6px;
  background: #fff;
  color: #1f2a44;
  font-size: 11px;
  cursor: pointer;
  margin-right: 2px;
  transition: all 0.15s ease;
}

.ne-topbar-btn:hover {
  background: #f8fbff;
  border-color: rgba(47, 123, 255, 0.3);
  color: #355ce0;
}

.ne-file-input {
  display: none;
}

/* ── 主体：上 prompt + 下控件 ── */
.ne-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  min-height: 0;
  overflow: hidden;
}

.ne-voice-wrap {
  padding: 0 12px 12px;
}

.ne-preview {
  flex-shrink: 0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px 0;
  cursor: pointer;
}

.ne-preview-img {
  max-width: 100%;
  max-height: 160px;
  object-fit: contain;
  border-radius: 8px;
  background: var(--glass-bg-muted, #f3f4f6);
  transition: transform 0.15s ease;
}

/* 视频缩略图：禁用内部交互，所有点击交给外层放大查看 */
.ne-preview-video-thumb {
  pointer-events: none;
}

.ne-preview:hover .ne-preview-img {
  transform: scale(1.01);
}

.ne-preview-zoom-hint {
  position: absolute;
  right: 16px;
  top: 12px;
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.55);
  color: #fff;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.ne-preview:hover .ne-preview-zoom-hint {
  opacity: 1;
}

/* ── 音频预览 ── */
.ne-audio-preview {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px 0;
}

.ne-audio-preview audio {
  width: 100%;
  height: 36px;
  border-radius: 8px;
}

.ne-audio-name {
  font-size: 11px;
  color: #6b7280;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 音频上传区 ── */
.ne-audio-upload-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 8px 0;
}

.ne-audio-upload-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  border: 1.5px dashed rgba(245, 158, 11, 0.35);
  border-radius: 12px;
  background: rgba(245, 158, 11, 0.04);
  color: #b45309;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ne-audio-upload-btn:hover:not(:disabled) {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.55);
}

.ne-audio-upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ne-audio-upload-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}

.ne-audio-upload-text {
  font-size: 13px;
  font-weight: 600;
  color: #92400e;
}

.ne-audio-upload-hint {
  font-size: 11px;
  color: #b45309;
  opacity: 0.8;
}

.ne-audio-uploaded {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 20px;
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 12px;
  background: #f9fafb;
}

.ne-audio-uploaded-info {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
}

.ne-audio-uploaded-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
  flex-shrink: 0;
}

.ne-audio-uploaded-name {
  font-size: 13px;
  font-weight: 500;
  color: #1f2a44;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ne-audio-reupload-btn {
  height: 30px;
  padding: 0 14px;
  border: 1px solid rgba(34, 57, 98, 0.12);
  border-radius: 6px;
  background: #fff;
  color: #1f2a44;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ne-audio-reupload-btn:hover:not(:disabled) {
  border-color: rgba(245, 158, 11, 0.45);
  color: #b45309;
  background: rgba(245, 158, 11, 0.05);
}

.ne-audio-reupload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── 音频节点控件栏 ── */
.ne-audio-controls {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #fff;
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 10px;
}

.ne-audio-ctrl-upload {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 6px;
  background: linear-gradient(180deg, #fbbf24, #f59e0b);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ne-audio-ctrl-upload:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(245, 158, 11, 0.32);
}

.ne-audio-ctrl-upload:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ne-audio-ctrl-hint {
  margin-left: auto;
  font-size: 11px;
  color: #9ca3af;
}
.ne-fullscreen-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  cursor: zoom-out;
  animation: neFadeIn 0.2s ease-out;
}

.ne-fullscreen-media {
  max-width: 92vw;
  max-height: 92vh;
  object-fit: contain;
  border-radius: 4px;
  cursor: default;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.4);
}

.ne-fullscreen-close {
  position: absolute;
  top: 24px;
  right: 24px;
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  cursor: pointer;
  transition: background 0.15s ease;
}

.ne-fullscreen-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

.ne-preview-fade-enter-active,
.ne-preview-fade-leave-active {
  transition: opacity 0.2s ease;
}

.ne-preview-fade-enter-from,
.ne-preview-fade-leave-to {
  opacity: 0;
}

.ne-prompt-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}

.ne-body-area {
  min-height: 120px;
  max-height: 300px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.ne-prompt-area {
  flex: 0 0 auto;
  border-top: 1px dashed rgba(34, 57, 98, 0.1);
  padding-top: 8px;
  margin-top: 4px;
}

.ne-prompt-input {
  flex: 1;
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  resize: vertical;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  color: #1f2a44;
  min-height: 60px;
}

.ne-prompt-input::placeholder {
  color: #9ca3af;
}

.ne-status-text {
  font-size: 11px;
  color: #6b7280;
  padding: 5px 8px;
  border-radius: 6px;
  background: #f3f6fb;
  border: 1px solid rgba(34, 57, 98, 0.06);
}

/* ── 控件栏（底部单行/换行） ── */
.ne-controls {
  flex: 0 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 8px;
  background: #f9fafb;
  border: 1px solid rgba(34, 57, 98, 0.06);
  border-radius: 10px;
}

.ne-ctrl-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 6px;
  background: #fff;
  color: #1f2a44;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ne-ctrl-btn:hover {
  background: #f8fbff;
  border-color: rgba(47, 123, 255, 0.3);
  color: #355ce0;
}

.ne-ctrl-btn svg {
  color: #6b7280;
}

.ne-segmented {
  display: inline-flex;
  align-items: center;
  background: #fff;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 8px;
  padding: 2px;
  gap: 2px;
}

.ne-seg-btn {
  height: 24px;
  min-width: 36px;
  padding: 0 8px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: #6b7280;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.12s ease;
}

.ne-seg-btn:hover {
  color: #1f2a44;
}

.ne-seg-btn.is-active {
  background: linear-gradient(180deg, #4b78ff, #355ce0);
  color: #fff;
}

.ne-format-group {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ne-fmt-btn {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 6px;
  background: #fff;
  color: #1f2a44;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ne-fmt-btn:hover {
  background: #f8fbff;
  border-color: rgba(47, 123, 255, 0.3);
  color: #355ce0;
}

.ne-fmt-bold { font-weight: 700; }
.ne-fmt-italic { font-style: italic; font-family: Georgia, serif; }

.ne-send-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 6px;
  background: linear-gradient(180deg, #4b78ff, #355ce0);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 10px rgba(75, 120, 255, 0.32);
  margin-left: auto;
}

.ne-send-btn:hover:not(:disabled) {
  background: linear-gradient(180deg, #5b88ff, #456ce8);
  transform: translateY(-1px);
}

.ne-send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
}

.ne-count-group {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ne-count-btn {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 5px;
  background: #fff;
  color: #52607a;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ne-count-btn:hover:not(:disabled) {
  background: #f8fbff;
  color: #1f2a44;
  border-color: rgba(47, 123, 255, 0.3);
}

.ne-count-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.ne-count-val {
  min-width: 26px;
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: #1f2a44;
  user-select: none;
}

.ne-icon-ctrl {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(34, 57, 98, 0.1);
  border-radius: 6px;
  background: #fff;
  color: #52607a;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ne-icon-ctrl:hover {
  background: #f8fbff;
  border-color: rgba(47, 123, 255, 0.3);
  color: #355ce0;
}

.ne-pending-tag {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(234, 179, 8, 0.1);
  color: #b45309;
  font-size: 11px;
  font-weight: 600;
  margin-left: auto;
}

/* ── 参考图缩略图 ── */
.ne-ref-area {
  flex: 0 0 auto;
  margin-top: 8px;
}

.ne-ref-thumbs {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.ne-ref-thumb-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ne-ref-thumb {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(34, 57, 98, 0.12);
  background: #f3f4f6;
}

.ne-ref-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* 视频引用：填满 ne-ref-thumb，叠加播放图标 */
.ne-ref-video {
  position: absolute;
  inset: 0;
}

.ne-ref-video img,
.ne-ref-video video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  pointer-events: none;
}

.ne-ref-video-play {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.95);
  pointer-events: none;
}

.ne-ref-video-play svg {
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.55));
}

/* 音频引用 chip：横向布局，区别于图片方形缩略图 */
.ne-ref-thumb.ne-ref-thumb-audio-card {
  width: auto;
  min-width: 96px;
  max-width: 160px;
  height: 40px;
  padding: 4px 8px;
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.3);
}

.ne-ref-audio {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  height: 100%;
  min-width: 0;
}

.ne-ref-audio-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.18);
  color: #d97706;
  flex-shrink: 0;
}

.ne-ref-audio-body {
  display: inline-flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  flex: 1;
}

.ne-ref-audio-name {
  font-size: 11px;
  font-weight: 600;
  color: #92400e;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ne-ref-audio-tag {
  font-size: 10px;
  color: #b45309;
  line-height: 1.1;
  opacity: 0.85;
}

.ne-ref-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  transition: background 0.15s ease;
}

.ne-ref-remove:hover {
  background: rgba(239, 68, 68, 0.9);
}

.ne-ref-swap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid rgba(111, 126, 153, 0.24);
  border-radius: 50%;
  background: #fff;
  color: #999;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}

.ne-ref-swap:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
}

.ne-ref-thumb {
  cursor: pointer;
}

.ne-ref-thumb-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  background: rgba(47, 123, 255, 0.08);
}

.ne-ref-text {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 10px;
  line-height: 1.4;
  color: #4b5563;
  text-align: left;
}

.ne-ref-type {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
}

.ne-ref-empty-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}

.ne-ref-empty-icon.ne-ref-empty-image { color: #3b82f6; opacity: 0.55; }
.ne-ref-empty-icon.ne-ref-empty-video { color: #8b5cf6; opacity: 0.55; }
.ne-ref-empty-icon.ne-ref-empty-audio { color: #f59e0b; opacity: 0.55; }

.ne-ref-role {
  position: absolute;
  right: 2px;
  bottom: 2px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #ff8a3d;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
}

.ne-ref-role[data-role="first_frame"] {
  background: #2ec1c0;
}

.ne-ref-role[data-role="last_frame"] {
  background: #ff5b8a;
}

.ne-ref-role[data-role="reference"] {
  background: #ff8a3d;
}

.ne-ref-area {
  margin-top: 0;
  margin-bottom: 0;
}

.ne-ref-area + .ne-prompt-area {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.ne-ref-uploading {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  height: 56px;
  border-radius: 8px;
  border: 1px dashed rgba(47, 123, 255, 0.35);
  background: rgba(47, 123, 255, 0.05);
  color: #355ce0;
  font-size: 11px;
}

.ne-ref-spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(53, 92, 224, 0.25);
  border-top-color: #355ce0;
  animation: neSpin 0.8s linear infinite;
}

@keyframes neSpin {
  to { transform: rotate(360deg); }
}

/* ── 拖拽遮罩 ── */
.ne-panel.ne-drag-active {
  outline: 2px dashed #2f7bff;
  outline-offset: -3px;
}

.ne-drop-overlay {
  position: absolute;
  inset: 8px;
  border-radius: 12px;
  background: rgba(47, 123, 255, 0.1);
  border: 2px dashed #2f7bff;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 50;
}

.ne-drop-text {
  padding: 8px 18px;
  background: #fff;
  color: #2f7bff;
  font-size: 13px;
  font-weight: 600;
  border-radius: 999px;
  box-shadow: 0 4px 14px rgba(47, 123, 255, 0.18);
}

/* ── 模型按钮 ── */
.ne-model-wrap {
  display: inline-flex;
}

.ne-ctrl-model {
  height: 28px;
  padding: 0 10px !important;
  background: #fff;
  border-color: rgba(34, 57, 98, 0.12);
  color: #1f2a44;
  font-weight: 500;
  transition: all 0.18s ease;
}

.ne-ctrl-model:hover {
  background: #f8fbff;
  border-color: rgba(47, 123, 255, 0.35);
  color: #355ce0;
  box-shadow: 0 1px 4px rgba(47, 123, 255, 0.08);
}

.ne-ctrl-model.is-active {
  background: linear-gradient(180deg, rgba(75, 120, 255, 0.08), rgba(53, 92, 224, 0.06));
  border-color: rgba(47, 123, 255, 0.45);
  color: #355ce0;
  box-shadow: 0 2px 8px rgba(47, 123, 255, 0.15);
}

.ne-ctrl-model .ne-model-icon {
  color: #6b7280;
  transition: color 0.18s ease;
}

.ne-ctrl-model:hover .ne-model-icon,
.ne-ctrl-model.is-active .ne-model-icon {
  color: #355ce0;
}

.ne-model-name {
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ne-model-name.is-placeholder {
  color: #9ca3af;
  font-weight: 400;
}

.ne-model-caret {
  color: #9ca3af;
  transition: transform 0.2s ease, color 0.18s ease;
}

.ne-ctrl-model.is-active .ne-model-caret {
  transform: rotate(180deg);
  color: #355ce0;
}

/* ── 模型下拉浮层（Teleport 到 body） ── */
.ne-model-menu {
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(34, 57, 98, 0.08);
  box-shadow: 0 12px 32px -8px rgba(15, 23, 42, 0.18), 0 4px 12px -4px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  max-height: 340px;
  display: flex;
  flex-direction: column;
  animation: neMenuIn 0.16s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes neMenuIn {
  from { opacity: 0; transform: translateY(-4px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0)   scale(1); }
}

.ne-mm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 8px;
  font-size: 11px;
  font-weight: 500;
  color: #6b7280;
  letter-spacing: 0.2px;
  border-bottom: 1px solid rgba(34, 57, 98, 0.06);
}

.ne-mm-loading {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #9ca3af;
}

.ne-mm-loading::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid rgba(107, 114, 128, 0.25);
  border-top-color: #6b7280;
  animation: neSpin 0.7s linear infinite;
}

.ne-mm-list {
  overflow-y: auto;
  padding: 4px;
}

.ne-mm-item {
  width: 100%;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease;
}

.ne-mm-item:hover {
  background: rgba(47, 123, 255, 0.06);
}

.ne-mm-item.is-selected {
  background: rgba(47, 123, 255, 0.1);
}

.ne-mm-item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ne-mm-name {
  font-size: 12.5px;
  font-weight: 500;
  color: #1f2a44;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ne-mm-item.is-selected .ne-mm-name {
  color: #355ce0;
  font-weight: 600;
}

.ne-mm-provider {
  font-size: 11px;
  color: #9ca3af;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ne-mm-check {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  margin-top: 2px;
  color: #355ce0;
  opacity: 0;
  transition: opacity 0.12s ease;
}

.ne-mm-item.is-selected .ne-mm-check {
  opacity: 1;
}

.ne-mm-empty {
  padding: 24px 14px;
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.6;
}

/* ── 视频节点横向下拉选择栏 ── */
.ne-video-controls {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: #fff;
  border: 1px solid rgba(34, 57, 98, 0.08);
  border-radius: 10px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
  flex-wrap: nowrap;
}

.ne-vs-select {
  height: 28px;
  min-width: 64px;
  max-width: 120px;
  flex: 1 1 0;
  padding: 0 18px 0 4px;
  border: none;
  border-radius: 6px;
  background: #fff;
  color: #1f2a44;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  outline: none;

  /* 各下拉按钮宽度（按 key 修饰） */
  &.ne-vs-key-model {
    flex: 1.6 1 0;
    min-width: 110px;
    max-width: 200px;
  }
  &.ne-vs-key-ratio,
  &.ne-vs-key-videoRatio,
  &.ne-vs-key-videoDuration,
  &.ne-vs-key-videoResolution,
  &.ne-vs-key-resolution,
  &.ne-vs-key-count {
    flex: 0 0 auto;
    min-width: 56px;
    max-width: 72px;
  }
  &.ne-vs-key-imageStyle,
  &.ne-vs-key-videoReferenceMode {
    flex: 1 1 0;
    min-width: 84px;
    max-width: 130px;
  }
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 24 24' fill='none' stroke='%239ca3af' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 4px center;
  transition: background-color 0.15s ease;
  display: inline-block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ne-vs-select:hover {
  background-color: #eff6ff;
  color: #355ce0;
}

.ne-vs-select:focus {
  background-color: #eff6ff;
  color: #355ce0;
}

/* 自定义模型下拉按钮（与 native select 视觉一致） */
.ne-vs-model {
  flex: 1 1 0;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 4px;
  background-image: none;
  background-color: #fff;
  text-align: left;
  border: none;
  min-width: 80px;
}

.ne-vs-model .ne-vs-caret {
  flex-shrink: 0;
  color: #9ca3af;
  transition: transform 0.2s ease, color 0.18s ease;
}

.ne-vs-model:hover {
  background-color: #eff6ff;
  color: #355ce0;
}

.ne-vs-model:hover .ne-vs-caret {
  color: #355ce0;
}

.ne-vs-model.is-active {
  background-color: #eff6ff;
  color: #355ce0;
}

.ne-vs-model.is-active .ne-vs-caret {
  transform: rotate(180deg);
  color: #355ce0;
}

.ne-vs-value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ne-vs-value.is-placeholder {
  color: #9ca3af;
  font-weight: 400;
}

/* 圆形提交按钮（最右侧） */
.ne-submit-circle {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: linear-gradient(180deg, #4b78ff, #355ce0);
  color: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 12px rgba(53, 92, 224, 0.35);
  margin-left: auto;
}

.ne-submit-circle:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(53, 92, 224, 0.45);
}

.ne-submit-circle:disabled {
  background: #c7ced9;
  cursor: not-allowed;
  box-shadow: none;
  opacity: 0.7;
}

/* 提交中状态：横向 spinner + 文案 */
.ne-submit-loading {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.ne-submit-loading svg {
  animation: neSubmitSpin 0.7s linear infinite;
}

.ne-submit-loading-text {
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

@keyframes neSubmitSpin {
  to { transform: rotate(360deg); }
}

/* 提示词输入框：视频/图片节点稍微拉高，支持拖拽调整高度 */
.ne-prompt-area.is-full :deep(.pme-editor) {
  min-height: 96px;
}

.ne-prompt-area.is-full :deep(.pme-shell) {
  min-height: 112px;
}
</style>
