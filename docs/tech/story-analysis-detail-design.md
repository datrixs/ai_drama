# 故事分析功能 — 详细技术设计

> 版本: v1.2 | 日期: 2026-05-22 | 作者: 架构师
> 关联文档: [系统架构设计 v1.1](drama-production-architecture.md) | [产品需求 v1.0](../products/v1.0-短剧Agent-故事分析.md)
>
> ### 版本变更
>
> | 版本 | 日期 | 变更内容 |
> |------|------|----------|
> | v1.0 | 2026-05-18 | 初始版本 |
> | v1.1 | 2026-05-20 | 新增十三、模型调用层架构设计（LiteLLM 引入方案 + LangGraph 分析）；新增十四、模型配置链路设计（项目配置 → 设置中心 → 运行时） |
> | v1.2 | 2026-05-22 | 根据代码实现同步更新：修正 Workflow 为串行执行、更新增量调整流程、补充实际 API 端点、修正数据存储和重试策略 |

---

## 一、需求与架构的差异分析

产品需求与系统架构之间存在以下需要明确的点：

| # | 产品需求 | 架构现状 | 需要细化 |
|---|----------|----------|----------|
| 1 | 点击「开始创作」后携带小说文本跳转至工作区 | 架构中 project 表需要 project_id | 需要确定项目何时创建：点击时立即创建 draft 项目 |
| 2 | 分析完成→弹出确认弹窗→用户填写项目信息→创建项目 | 架构中 project 表有 title/ratio/style 等字段 | 需要确定先分析后建项目的数据暂存方案 |
| 3 | 多人同时进入同一项目设置，以最后一个为准 | 架构中无并发控制设计 | 需要乐观锁/最后写入胜出策略 |
| 4 | 第一集分镜支持用户手动编辑和保存 | 架构中 first_ep_storyboard 存在 analysis_version 的 JSONB 字段中 | 需要确定编辑后的存储和版本管理 |
| 5 | 重新进入未设置的项目时弹出设置弹窗 | 需要状态判断 | 需要明确状态流转和前端判断逻辑 |
| 6 | 产品提到项目配置包含多个模型选择 | 架构中 project 表无模型配置字段 | 需要在 project 表增加 config JSONB |

### 1.1 关键决策：项目何时创建

**决策：点击「开始创作」时立即创建 draft 项目**

理由：
- 后续所有操作（分析、文件上传、日志）都需要 project_id 作为上下文
- 多人场景要求项目已存在才能进入同一页面
- WebSocket 订阅和 Redis 缓冲区都以 project_id 为 key
- 分析前的「暂存」状态用 project.status = `draft` 表达

```
首页点击「开始创作」
    │
    ▼
POST /api/v1/projects  (创建 draft 项目, 携带 novel_text)
    │
    ▼ 返回 project_id
前端跳转至 /workspace/{project_id}?tab=story
    │
    ▼
自动触发分析任务 (PUT /api/v1/projects/{id}/analyze)
    │
    ▼
分析完成 → WS 推送 → 弹出确认弹窗
    │
    ▼
用户确认 → PUT /api/v1/projects/{id}/confirm  (填写 title/ratio/style)
    │
    ▼
status: draft → projectCreated
```

---

## 二、状态机设计

### 2.1 项目状态（project.status）

```
draft                 用户点击「开始创作」后立即创建，尚未开始分析
  │
  ▼ PUT /analyze
analyzingStory        AI 正在分析小说
  │
  ▼ 分析完成
storyReady            分析完成，等待用户确认项目设置（弹窗）
  │
  ▼ PUT /confirm
projectCreated        项目已确认，展示分析结果，可调整
  │
  ▼ 用户点击「下一步」
assetsReady           进入资产库阶段（后续功能）
  │
  ▼
producing             进入视频制作阶段
  │
  ▼
completed             全部完成
```

### 2.2 分析结果状态（analysis_result.status）

```
pending               刚创建，未开始
  │
  ▼
generating            正在生成（串行执行各子任务）
  │
  ├─ ▼ 全部子项完成
  │  completed             分析完成，可用于展示和调整
  │
  └─ ▼ 生成失败
     failed                分析失败（Workflow 异常时回退设置）
```

### 2.3 前端页面状态映射

| project.status | 前端展示 |
|----------------|----------|
| draft | Loading 状态（刚跳转，分析即将开始） |
| analyzingStory | Loading 状态（「正在研读故事内核，构思视觉风格...」） |
| storyReady | 确认弹窗 |
| projectCreated | 五部分内容卡片 + 调整输入框 + 「下一步」按钮 |

---

## 三、API 设计

### 3.1 接口列表

| 方法 | 路径 | 说明 | 触发时机 |
|------|------|------|----------|
| POST | `/api/v1/projects` | 创建 draft 项目 | 首页点击「开始创作」 |
| PUT | `/api/v1/projects/{id}/analyze` | 触发故事分析 | 自动触发 / 点击「发送」调整 |
| PUT | `/api/v1/projects/{id}/confirm` | 确认项目设置 | 确认弹窗点击「确认」 |
| GET | `/api/v1/projects/{id}` | 获取项目详情（含状态） | 页面加载/刷新 |
| GET | `/api/v1/projects/{id}/analysis` | 获取最新分析结果 | 页面加载/WS 通知后 |
| PUT | `/api/v1/projects/{id}/analysis/storyboard` | 保存手动编辑的第一集分镜 | 用户编辑第一集分镜后保存 |
| POST | `/api/v1/upload/novel` | 上传小说文件 | 上传 TXT/DOCX |
| GET | `/api/v1/projects/check_analysis_model_config` | 校验用户是否配置必要模型 | 进入故事分析前校验 |
| POST | `/api/v1/projects/ai_story_expand` | AI 故事扩写 | 用户输入短创意，扩写为完整故事 |

### 3.2 接口详细设计

#### POST /api/v1/projects — 创建项目

```
请求:
{
    "novel_text": "小说正文内容...",    // 至少20字符
    "file_url": "minio://novels/xxx.txt"  // 可选，如果从文件上传
}

响应:
{
    "id": "proj_id",
    "status": "draft",
    "create_time": "2026-05-18T10:30:00Z"
}

逻辑:
1. 校验 novel_text 长度 >= 20
2. 创建 project (status=draft, novel_text 存入)
3. 创建 analysis_result (status=pending)
4. 异步上传小说文本到云存储
5. 返回 project_id
```

#### PUT /api/v1/projects/{id}/analyze — 触发/调整分析

```
请求:
{
    "adjustment": null           // 首次分析时为 null
}

或:
{
    "adjustment": "让主角的性格更硬朗一些，场景描写增加更多细节"  // 调整时传入
}

响应:
{
    "task_id": "task_id",
    "project_status": "analyzingStory"
}

逻辑:
首次分析 (adjustment == null):
  1. 校验 project.status == draft
  2. 更新 project.status = analyzingStory
  3. 创建 analysis_version (version_number=1, parent_version_id=null)
  4. 提交 Celery Workflow 任务
  5. 返回 task_id

调整 (adjustment != null):
  1. 校验 project.status == projectCreated
  2. 更新 project.status = analyzingStory
  3. 创建 analysis_version (version_number=N+1, parent_version_id=当前版本id)
  4. 从当前版本的 adjustment_context 构建增量上下文
  5. 提交 Celery 增量调整任务
  6. 返回 task_id
```

#### PUT /api/v1/projects/{id}/confirm — 确认项目设置

```
请求:
{
    "title": "我的短剧项目",
    "ratio": "9:16",            // 9:16 / 16:9 / 3:4 / 1:1
    "style": "realistic"        // realistic / anime / watercolor / oil
}

响应:
{
    "id": "proj_xxx",
    "status": "projectCreated",
    "title": "我的短剧项目",
    "config": {
        "ratio": "9:16",
        "style": "realistic",
        "video_resolution": "1080x1920",
        "image_resolution": "1024x1024"
    }
}

逻辑:
1. 校验 project.status == storyReady
2. 更新 project.title, project.config
3. 更新 project.status = projectCreated
4. 记录 operation_record
5. 最后写入胜出：不做乐观锁，直接覆盖（满足需求"以最后一个为准"）
```

#### GET /api/v1/projects/{id} — 获取项目详情

```
响应:
{
    "id": "proj_xxx",
    "title": "我的短剧项目",
    "status": "projectCreated",
    "phase": "text_analysis",
    "config": {
        "ratio": "9:16",
        "style": "realistic",
        "video_resolution": "1080x1920",
        "image_resolution": "1024x1024",
        "text_model": "deepseek-v3",
        "character_model": "flux-pro",
        "scene_model": "flux-pro",
        "storyboard_model": "flux-pro",
        "image_edit_model": "flux-pro",
        "video_model": "kling-v1",
        "tts_model": "cosyvoice-v1"
    },
    "novel_meta": {
        "char_count": 50000,
        "chapter_count": 12,
        "format": "txt",
        "file_name": "novel.txt"
    },
    "analysis_status": "completed",
    "current_version_number": 1,
    "create_time": "...",
    "update_time": "..."
}
```

#### GET /api/v1/projects/{id}/analysis — 获取分析结果

```
响应:
{
    "version_id": "ver_xxx",
    "version_number": 1,
    "is_confirmed": false,
    "global_setting": { ... },
    "episode_outlines": [
        {"episode_number": 1, "title": "开端", "summary": "..."},
        {"episode_number": 2, "title": "冲突", "summary": "..."}
    ],
    "character_profiles": "[{\"name\": \"张三\", ...}]",           # Layer 2 模型原始输出字符串（JSON 序列化）
    "scene_descriptions": "[{\"name\": \"老街巷口\", ...}]",      # Layer 2 模型原始输出字符串（JSON 序列化）
    "prop_descriptions": "[{\"name\": \"黄铜钥匙\", ...}]",      # Layer 2 模型原始输出字符串（JSON 序列化）
    "first_ep_storyboard": {
        "scenes": [
            {
                "scene_number": 1,
                "location": "办公室",
                "characters": ["张三", "李四"],
                "action": "张三推门而入...",
                "dialogue": "张三：...",
                "camera": "中景，从门口推向张三",
                "duration": 5
            }
        ]
    }
}

注意:
- character_profiles / scene_descriptions / prop_descriptions 为模型原始输出字符串，前端需 JSON.parse() 解析
- character_details / scene_details / prop_details（Layer 1 原始数据）未通过此接口返回，也未在 Workflow 中持久化到 AnalysisVersion
```

#### PUT /api/v1/projects/{id}/analysis/storyboard — 保存手动编辑的分镜

```
请求:
{
    "storyboard": {
        "scenes": [...]    // 用户编辑后的第一集分镜完整数据
    }
}

响应:
{
    "version_id": "ver_xxx",
    "updated": true
}

逻辑:
1. 校验 project.status == projectCreated
2. 更新当前 analysis_version.first_ep_storyboard
3. 不创建新版本（手动编辑不触发版本链，直接更新当前版本）
```

#### POST /api/v1/upload/novel — 上传小说文件

```
请求: multipart/form-data
  file: novel.txt / novel.docx

响应:
{
    "file_url": "minio://novels/2026/05/18/xxx.txt",
    "extracted_text": "小说正文内容...",
    "char_count": 50000,
    "format": "txt"
}

逻辑:
1. 校验文件格式（仅 .txt / .docx）
2. 提取纯文本（docx 使用 python-docx）
3. 上传原始文件到云存储
4. 返回提取的文本和元信息
```

---

## 四、数据模型变更

### 4.1 project 表新增字段

在系统架构 v1.1 的 project 表基础上，新增 `config` JSONB 字段存储项目配置：

```sql
-- 在 project 表中新增
ALTER TABLE project ADD COLUMN config JSONB DEFAULT '{}';

-- config 结构:
-- {
--   "ratio": "9:16",
--   "style": "realistic",
--   "video_resolution": "1080x1920",
--   "image_resolution": "1024x1024",
--   "text_model": "deepseek-v3",
--   "character_model": "flux-pro",
--   "scene_model": "flux-pro",
--   "storyboard_model": "flux-pro",
--   "image_edit_model": "flux-pro",
--   "video_model": "kling-v1",
--   "tts_model": "cosyvoice-v1"
-- }
```

### 4.2 project 表状态值更新

```
原: draft/analyzing/assets_ready/producing/completed
新: draft/analyzingStory/storyReady/projectCreated/assetsReady/producing/completed
```

### 4.3 novel_file 关联

原始小说文件存储在云存储，路径规则：

```
{bucket}/novels/{project_id}/novel.{txt|docx}
```

`project.novel_meta` 记录文件元信息，`project.novel_text` 存储提取后的纯文本。

### 4.4 analysis_version 表字段使用说明

`AnalysisVersion` 模型中以下字段已在数据库定义，但 **Workflow 当前未写入**：

| 字段 | 用途 | 当前状态 |
|------|------|----------|
| `character_details` | Layer 1 人物原始结构化数据 | 未写入（仅 Layer 2 `character_profiles` 被写入） |
| `scene_details` | Layer 1 场景原始结构化数据 | 未写入（仅 Layer 2 `scene_descriptions` 被写入） |
| `prop_details` | Layer 1 道具原始结构化数据 | 未写入（仅 Layer 2 `prop_descriptions` 被写入） |
| `model_config_data` | 模型配置快照 | 未写入（`model_config` 通过参数传入但未持久化到此字段） |
| `prompt_snapshot` | Prompt 快照 | 未写入 |

> **已知问题**：Layer 1 原始数据在 `comprehensive_extraction` 中提取后仅用于传递给 Layer 2 子任务，未持久化到数据库。如后续需要访问原始提取数据（如资产库的 `profile_data` 字段），需补充写入逻辑。

---

## 五、Celery 任务设计

### 5.1 任务清单

| 任务名 | 类型 | 队列 | 超时 | 说明 |
|--------|------|------|------|------|
| `novel_preprocess` | 原子任务 | text | 60s | 小说预处理：分章、元信息 |
| `comprehensive_extraction` | 原子任务 | text | 180s | 详尽提取：唯一接触完整小说的步骤，提取故事概要/人物细节/场景细节/道具细节/章节摘要/集数建议。小说文本截断至 60000 字符 |
| `character_gen` | 原子任务 | text | 90s | 格式化润色人物特征（基于提取结果，不接触原文） |
| `scene_gen` | 原子任务 | text | 90s | 格式化润色场景描写（基于提取结果，不接触原文） |
| `prop_gen` | 原子任务 | text | 90s | 格式化润色道具描写（基于提取结果，不接触原文） |
| `episode_outline_gen` | 原子任务 | text | 120s | 生成每集大纲（基于提取结果，串行执行） |
| `first_ep_storyboard_gen` | 原子任务 | text | 120s | 生成第一集分镜（依赖 Layer 2 全部结果） |
| `story_analysis_workflow` | **Workflow** | text | 600s | 编排上述任务的分层串行流程（子任务作为普通函数调用，非独立 Celery 任务分发） |
| `story_analysis_adjust` | **Workflow** | text | 300s | 增量调整流程（单次模型调用） |

### 5.2 首次分析 Workflow

> **关键设计原则：Layer 1（comprehensive_extraction）是唯一接触完整小说的环节，必须做详尽提取，不能只输出摘要。**
> Layer 2 不接触原文，只做格式化润色——将 Layer 1 提取的原始细节组织成适合图片生成的标准化描写。
> 这样避免 Layer 2 凭空编造，保留小说中的真实细节。

```python
@celery.task(bind=True, name="story_analysis_workflow", time_limit=600, max_retries=1)
def story_analysis_workflow(self, project_id: str, version_id: str, model_config: dict):
    """首次分析 Workflow - 串行执行分层依赖任务"""
    db = SessionLocal()
    plog = get_project_logger(project_id)
    try:
        proj = _get_project(db, project_id)
        user_id = proj.user_id

        # === Layer 0: 小说预处理 ===
        _notify_progress(project_id, user_id, "preprocess", 5)
        preprocess_result = novel_preprocess(project_id)
        # preprocess_result: {novel_text, chapters, novel_meta}

        # === Layer 1: 详尽提取（串行，唯一接触完整小说的步骤） ===
        # 小说文本截断至 60000 字符，避免超出模型上下文
        _notify_progress(project_id, user_id, "extraction", 15)
        extraction = comprehensive_extraction(
            project_id=project_id,
            version_id=version_id,
            novel_text=preprocess_result["novel_text"],
            novel_meta=preprocess_result["novel_meta"],
            model_config=model_config,
        )

        # extraction 结构:
        # {
        #   "novel_summary": "故事概要",
        #   "world_setting": "世界观",
        #   "style_tone": "风格基调",
        #   "character_relations": "人物关系描述",
        #   "character_details": [{name, role, raw_appearance, raw_personality, key_behaviors, relationships, arc}],
        #   "scene_details": [{name, type, raw_description, spatial_layout, lighting, atmosphere}],
        #   "prop_details": [{name, importance, raw_description, usage_context, symbolic_meaning}],
        #   "chapter_summaries": [...],
        #   "suggested_episodes": 10,
        #   "episode_mapping": [...]
        # }

        # 构建增量上下文快照
        context_snapshot = _build_initial_context(extraction)

        # === Layer 2: 格式化润色（串行执行） ===
        # 每个子任务作为普通函数调用（同步执行，非独立 Celery 任务）
        _notify_progress(project_id, user_id, "layer2_start", 30)

        char_result = character_gen(
            project_id, version_id,
            extraction.get("character_details", []),
            extraction.get("character_relations", ""),
            model_config,
        )
        _notify_progress(project_id, user_id, "character", 45)

        scene_result = scene_gen(
            project_id, version_id,
            extraction.get("scene_details", []),
            model_config,
        )
        _notify_progress(project_id, user_id, "scene", 55)

        prop_result = prop_gen(
            project_id, version_id,
            extraction.get("prop_details", []),
            model_config,
        )
        _notify_progress(project_id, user_id, "prop", 65)

        outline_result = episode_outline_gen(
            project_id, version_id,
            extraction, preprocess_result["chapters"],
            model_config,
        )
        _notify_progress(project_id, user_id, "outline", 75)

        # === Layer 3: 第一集分镜（串行，依赖 Layer 2 结果） ===
        first_outline = outline_result.get("outlines", [{}])[0] if outline_result.get("outlines") else {}
        storyboard_result = first_ep_storyboard_gen(
            project_id, version_id,
            extraction, first_outline,
            char_result, scene_result,
            model_config,
        )
        _notify_progress(project_id, user_id, "storyboard", 90)

        # === 汇总写入数据库 ===
        # 注意：char_result / scene_result / prop_result 是模型原始输出字符串（非解析后的 JSON 数组）
        # Layer 1 原始数据（character_details/scene_details/prop_details）未持久化到 AnalysisVersion
        version = _get_version(db, version_id)
        version.global_setting = {
            "novel_summary": extraction.get("novel_summary", ""),
            "world_setting": extraction.get("world_setting", ""),
            "style_tone": extraction.get("style_tone", ""),
            "character_relations": extraction.get("character_relations", ""),
            "suggested_episodes": extraction.get("suggested_episodes", 0),
            "episode_mapping": extraction.get("episode_mapping", []),
        }
        version.character_profiles = char_result       # Layer 2 模型原始输出字符串
        version.scene_descriptions = scene_result       # Layer 2 模型原始输出字符串
        version.prop_descriptions = prop_result         # Layer 2 模型原始输出字符串
        version.episode_outlines = outline_result.get("outlines", [])
        version.first_ep_storyboard = storyboard_result
        version.adjustment_context = context_snapshot
        db.add(version)

        # 更新项目状态
        proj = _get_project(db, project_id)
        proj.status = "storyReady"
        db.add(proj)

        # 更新分析结果
        result = ar_crud.get_by_project(db, project_id)
        if result:
            result.status = "completed"
            result.current_version_id = version_id
            db.add(result)

        db.commit()

        ws_manager.publish_project_event(
            user_id=user_id,
            project_id=project_id,
            event_type="analysis_completed",
            data={"version_id": version_id, "project_status": "storyReady"},
        )

    except Exception as exc:
        plog.error(f"故事分析 Workflow 失败 error={exc}")
        try:
            _update_project_status(db, project_id, "draft")
            _update_analysis_status(db, project_id, "failed")
            proj = _get_project(db, project_id)
            ws_manager.publish_project_event(
                user_id=proj.user_id,
                project_id=project_id,
                event_type="analysis_failed",
                data={"error_message": str(exc)},
            )
        except Exception as inner_exc:
            logger.error(f"失败处理异常: {inner_exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
```

### 5.3 增量调整 Workflow

```python
@celery.task(bind=True, name="story_analysis_adjust", time_limit=300, max_retries=2)
def story_analysis_adjust(self, project_id: str, version_id: str, adjustment: str, model_config: dict):
    """增量调整 Workflow"""
    db = SessionLocal()
    plog = get_project_logger(project_id)
    try:
        proj = _get_project(db, project_id)
        user_id = proj.user_id

        result = ar_crud.get_by_project(db, project_id)
        current_version = av_crud.get_current_version(db, result.id)

        context_snapshot = current_version.adjustment_context or {}
        adjustment_history = context_snapshot.get("adjustment_history", [])

        # 构建增量 Prompt：传入完整上下文 + 调整历史 + 用户指令
        caller = ModelCaller.from_config_snapshot(model_config)
        prompt = INCREMENTAL_ADJUSTMENT_PROMPT.format(
            context_snapshot=json.dumps({
                "novel_summary": context_snapshot.get("novel_summary", ""),
                "world_setting": context_snapshot.get("world_setting", ""),
                "style_tone": context_snapshot.get("style_tone", ""),
                "character_relations": context_snapshot.get("character_relations", ""),
                "current_character_profiles": current_version.character_profiles,
                "current_scene_descriptions": current_version.scene_descriptions,
                "current_prop_descriptions": current_version.prop_descriptions,
                "current_episode_outlines": current_version.episode_outlines,
                "current_first_ep_storyboard": current_version.first_ep_storyboard,
            }, ensure_ascii=False, default=str),
            adjustment_history=json.dumps(adjustment_history, ensure_ascii=False),
            user_instruction=adjustment,
        )

        _notify_progress(project_id, user_id, "adjustment_start", 30)
        model_result = caller.call(
            model_key="analysis_model", prompt=prompt,
            temperature=0.5, max_tokens=8192, timeout=180,
            project_id=project_id, task_id=self.request.id,
        )
        _notify_progress(project_id, user_id, "adjustment_done", 80)

        # 解析模型返回，提取修改的子项
        updated = _safe_parse_json(model_result.content)
        change_summary = updated.pop("change_summary", "")

        # 合并：逐字段判断，非空则使用新值，空则继承上一版本
        new_version = _get_version(db, version_id)
        if "global_setting" in updated and updated["global_setting"]:
            new_version.global_setting = updated["global_setting"]
        else:
            new_version.global_setting = current_version.global_setting

        if "character_profiles" in updated and updated["character_profiles"]:
            new_version.character_profiles = updated["character_profiles"]
        else:
            new_version.character_profiles = current_version.character_profiles

        if "scene_descriptions" in updated and updated["scene_descriptions"]:
            new_version.scene_descriptions = updated["scene_descriptions"]
        else:
            new_version.scene_descriptions = current_version.scene_descriptions

        if "prop_descriptions" in updated and updated["prop_descriptions"]:
            new_version.prop_descriptions = updated["prop_descriptions"]
        else:
            new_version.prop_descriptions = current_version.prop_descriptions

        if "episode_outlines" in updated and updated["episode_outlines"]:
            new_version.episode_outlines = updated["episode_outlines"]
        else:
            new_version.episode_outlines = current_version.episode_outlines

        if "first_ep_storyboard" in updated and updated["first_ep_storyboard"]:
            new_version.first_ep_storyboard = updated["first_ep_storyboard"]
        else:
            new_version.first_ep_storyboard = current_version.first_ep_storyboard

        # 更新调整历史和上下文快照
        context_snapshot["adjustment_history"] = adjustment_history + [
            {
                "turn": new_version.version_number - 1,
                "instruction": adjustment,
                "summary_of_changes": change_summary,
            }
        ]
        context_snapshot["current_character_profiles"] = new_version.character_profiles
        context_snapshot["current_scene_descriptions"] = new_version.scene_descriptions
        context_snapshot["current_prop_descriptions"] = new_version.prop_descriptions
        context_snapshot["current_episode_outlines"] = new_version.episode_outlines
        context_snapshot["current_first_ep_storyboard"] = new_version.first_ep_storyboard

        new_version.adjustment_context = context_snapshot
        db.add(new_version)

        proj = _get_project(db, project_id)
        proj.status = "projectCreated"
        db.add(proj)

        result.status = "completed"
        result.current_version_id = version_id
        db.add(result)

        db.commit()

        ws_manager.publish_project_event(
            user_id=user_id,
            project_id=project_id,
            event_type="adjustment_completed",
            data={"version_id": version_id, "project_status": "projectCreated"},
        )

    except Exception as exc:
        plog.error(f"增量调整失败 error={exc}")
        try:
            _update_project_status(db, project_id, "projectCreated")
            proj = _get_project(db, project_id)
            ws_manager.publish_project_event(
                user_id=proj.user_id,
                project_id=project_id,
                event_type="adjustment_failed",
                data={"error_message": str(exc)},
            )
        except Exception as inner_exc:
            logger.error(f"失败处理异常: {inner_exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
```

> **关键差异（相比首次分析 Workflow）**：
> 1. 新版本在 API 端点中创建（非 Workflow 内部创建），Workflow 直接接收 `version_id`
> 2. 增量调整为单次模型调用，传入完整上下文快照 + 调整历史 + 用户指令
> 3. 合并策略：逐字段判断，非空使用新值，空则继承上一版本
> 4. context_snapshot 记录所有当前数据字段（含 profiles/outlines/storyboard），不仅是初始摘要

---

## 六、Prompt 设计

> **核心原则**：Layer 1（comprehensive_extraction）是唯一接触完整小说的步骤，必须做详尽提取；
> Layer 2 各子任务只做格式化润色，将原始提取转为适合图片生成的标准化描写。

### 6.1 详尽提取 Prompt（comprehensive_extraction，Layer 1）

```
你是一个专业的短剧编剧。请仔细阅读以下小说文本，进行详尽的内容提取。
你的提取结果将作为后续所有分析的原始素材，因此必须尽可能保留原文中的视觉细节。

## 小说文本
{novel_text}

## 输出要求
请以 JSON 格式输出以下内容：

{
    "novel_summary": "故事概要（500-1000字，包含核心情节、人物弧线、关键冲突）",
    "world_setting": "世界观描述（时代背景、社会环境、核心规则）",
    "style_tone": "风格基调（悬疑/轻松/热血/治愈等）",
    "character_relations": "人物关系图谱的文字描述，说明各角色之间的关系和冲突",

    "character_details": [
        {
            "name": "角色名",
            "role": "主角/配角/反派/路人",
            "raw_appearance": "从原文中提取的外貌描写原文或转述，要保留所有视觉细节：发型、肤色、体型、穿着、标志性特征（伤疤、痣、饰品等）。不要概括，要具体。",
            "raw_personality": "从原文中提取的性格描写，包含核心性格、行为模式、典型反应",
            "key_behaviors": ["这个角色做了什么关键的事", "另一个关键行为"],
            "key_dialogues": ["角色的典型台词或口头禅（原文）"],
            "relationships": "与哪些角色是什么关系，关键互动",
            "arc": "人物弧线：从...状态到...状态的转变"
        }
    ],

    "scene_details": [
        {
            "name": "场景名",
            "type": "室内/室外",
            "raw_description": "从原文中提取的环境描写原文或转述，保留所有感官细节：视觉、听觉、嗅觉、触觉。不要概括，要具体。",
            "spatial_layout": "空间布局描述（前后左右有什么、远近关系）",
            "lighting": "光线描述（自然光/人工光、明暗、色温）",
            "time_of_day": "白天/夜晚/黄昏/清晨",
            "weather": "天气（如有描写）",
            "atmosphere": "氛围关键词（3-5个词）",
            "fixed_objects": ["场景中固定存在的物品"]
        }
    ],

    "prop_details": [
        {
            "name": "道具名",
            "importance": "关键/普通",
            "raw_description": "从原文中提取的道具外观描写，保留所有视觉细节：材质、颜色、形状、大小、磨损、刻字、装饰等",
            "usage_context": "在什么场景中由谁使用，用于做什么",
            "symbolic_meaning": "象征意义（如有）"
        }
    ],

    "chapter_summaries": [
        {"chapter_number": 1, "title": "章节标题", "summary": "本章内容摘要（100-200字）"}
    ],

    "suggested_episodes": 10,
    "episode_mapping": [
        {"episode": 1, "chapters": "第1-3章", "theme": "开端"},
        {"episode": 2, "chapters": "第4-6章", "theme": "冲突升级"}
    ]
}

## 关键注意事项
- character_details 中的 raw_appearance 是最核心的字段，将直接用于生成角色图片，必须详尽
  ❌ 错误示例: "穿着朴素" "长相普通"
  ✅ 正确示例: "穿着洗得发白的蓝色工装，袖口挽到手肘，露出黝黑的小臂"
- scene_details 中的 raw_description 同样核心，将直接用于生成场景图片
  ❌ 错误示例: "一条老街"
  ✅ 正确示例: "老街两侧是青砖灰瓦的老房子，屋檐下挂着褪色的红灯笼，地面是坑洼的石板路"
- prop_details 中的 raw_description 必须包含足够的视觉细节
  ❌ 错误示例: "一把钥匙"
  ✅ 正确示例: "黄铜钥匙已经氧化发绿，钥匙柄上刻着一个模糊的'陈'字"
- 如果原文中对某个角色的外貌描写分散在多处，请合并到 raw_appearance 中
- 如果原文中对某个角色的外貌描写很少，请在 raw_appearance 中标注"原文描写不足"，并基于角色设定合理补充
- 人物列表要完整，包括所有有台词的角色
- 场景列表要覆盖所有关键场景
- 集数建议基于故事体量，通常每集3-5分钟
```

### 6.2 人物特征格式化 Prompt（character_gen，Layer 2）

```
你是一个短剧角色设计师。以下是从小说中提取的角色原始信息，请将其格式化为标准的角色描写，
用于指导角色图片生成。

## 角色原始信息
{character_details}

## 人物关系
{character_relations}

## 输出要求
请以 JSON 数组格式输出每个角色的标准描写：

```json
[
  {
    "name": "角色名",
    "role": "主角/配角/反派/路人",
    "description": "角色的完整格式化描写，包含外貌特征、性格特征、人物弧线、关键关系等，适合用于图片生成的详细描述文本",
    "image_prompt": "中文逗号分隔的视觉关键词，如：年轻女性，黑色微卷长发，左耳垂有小痣，蓝色工装，袖口挽起，黝黑皮肤"
  }
]
```

其中 `description` 是完整的角色描写文本（外貌+性格+弧线+关系），`image_prompt` 是浓缩的视觉关键词，直接用于图片模型。

## 注意事项
- description 和 image_prompt 必须基于上方的原始信息，不要编造原文没有的细节
- 如果原始信息标注了"原文描写不足"，请在保留已有细节的基础上合理补充，并标注[补充]标记
- 每个角色的视觉特征要独特，避免角色之间混淆
- 穿着描述要考虑角色在不同场景的换装（如有）
```

### 6.3 场景描写格式化 Prompt（scene_gen，Layer 2）

```
你是一个短剧场景设计师。以下是从小说中提取的场景原始信息，请将其格式化为标准的场景描写，
用于指导场景图片生成。

## 场景原始信息
{scene_details}

## 输出要求
请以 JSON 数组格式输出每个场景的标准描写：

```json
[
  {
    "name": "场景名",
    "type": "室内/室外",
    "summary": "3-5个氛围关键词，如：烟火气、怀旧、温暖",
    "description": "场景的完整格式化描写，包含环境描述、色彩基调、光线氛围、关键道具等，适合用于图片生成的详细描述文本",
    "image_prompt": "中文逗号分隔的视觉关键词，如：老街，青砖灰瓦老房子，屋檐下褪色红灯笼，石板路，清晨薄雾"
  }
]
```

## 注意事项
- description 和 image_prompt 必须基于上方的原始信息，不要编造原文没有的细节
- 如果原始信息描写不足，合理补充并标注[补充]标记
- 场景之间要有视觉差异化
```

### 6.4 道具描写格式化 Prompt（prop_gen，Layer 2）

```
你是一个短剧道具设计师。以下是从小说中提取的道具原始信息，请将其格式化为标准的道具描写，
用于指导道具图片生成。

## 道具原始信息
{prop_details}

## 输出要求
请以 JSON 数组格式输出每个道具的标准描写：

```json
[
  {
    "name": "道具名",
    "importance": "关键/普通",
    "description": "道具的完整格式化描写，包含外观描述、细节特征、使用场景、象征意义等，适合用于图片生成的详细描述文本",
    "image_prompt": "中文逗号分隔的视觉关键词，如：老旧黄铜钥匙，氧化发绿，钥匙柄刻有模糊的陈字，磨损的齿痕"
  }
]
```

## 注意事项
- description 和 image_prompt 必须基于上方的原始信息，不要编造原文没有的细节
- 如果原始信息描写不足，合理补充并标注[补充]标记
```

### 6.5 每集大纲 Prompt

```
基于以下短剧全局设定和章节映射，为每集生成剧本大纲。

## 故事概要与世界观
{novel_summary}
{world_setting}

## 人物关系
{character_relations}

## 章节摘要
{chapter_summaries}

## 集数映射建议
{episode_mapping}

## 输出要求
请以 JSON 格式输出每集大纲：

[
    {
        "episode_number": 1,
        "title": "集标题",
        "summary": "本集剧情摘要（200-300字）",
        "key_events": ["关键事件1", "关键事件2"],
        "key_characters": ["本集关键角色"],
        "cliffhanger": "本集结尾悬念"
    },
    ...
]

注意：
- 每集要有明确的开头、冲突和结尾
- 集与集之间要有连贯性
- 每集结尾最好有悬念或转折
- key_characters 要与提取的角色列表对应
```

### 6.6 第一集分镜 Prompt（first_ep_storyboard_gen，Layer 3）

```
基于以下信息，为第一集生成详细的分镜剧本。

## 故事概要
{novel_summary}

## 第一集大纲
{first_episode_outline}

## 人物特征（已格式化）
{character_profiles}

## 场景描写（已格式化）
{scene_descriptions}

## 角色原始细节（用于补充分镜中的角色行为）
{character_details_raw}

## 输出要求
请以 JSON 格式输出分镜内容：

{
    "scenes": [
        {
            "scene_number": 1,
            "location": "场景名（必须与场景列表中的名称一致）",
            "time": "白天/夜晚/黄昏",
            "characters": ["出场角色列表"],
            "action": "角色动作和画面描述",
            "dialogue": "角色对白（如有，尽量使用原文对话）",
            "camera": "镜头运动描述（推/拉/摇/移/跟）",
            "emotion": "情绪氛围",
            "duration": 5
        }
    ]
}

注意：
- 每个分镜时长不超过15秒
- 动作描写要可视化，适合直接生成视频
- 角色外貌和行为要与人物特征描述一致
- 场景描写要与场景列表中的视觉细节一致
- 对白尽量使用原文中的对话，保留角色语言特色
- 镜头语言要专业
- 分镜数量控制在 15-30 个（对应 3-5 分钟视频）
```

---

## 七、前后端交互时序

### 7.1 首次分析完整时序

```
前端                         FastAPI                     Celery Worker              模型 API
 │                              │                            │                         │
 │  POST /projects              │                            │                         │
 │  {novel_text}                │                            │                         │
 │─────────────────────────────▶│                            │                         │
 │                              │ 创建 project (draft)       │                         │
 │                              │ 创建 analysis_result       │                         │
 │  {project_id}                │                            │                         │
 │◀─────────────────────────────│                            │                         │
 │                              │                            │                         │
 │  跳转 /workspace/{id}        │                            │                         │
 │                              │                            │                         │
 │  PUT /projects/{id}/analyze  │                            │                         │
 │  {adjustment: null}          │                            │                         │
 │─────────────────────────────▶│                            │                         │
 │                              │ status=draft→analyzingStory│                         │
 │                              │ 创建 analysis_version v1   │                         │
 │                              │ 提交 workflow task ────────▶│                         │
 │  {task_id}                   │                            │                         │
 │◀─────────────────────────────│                            │                         │
 │                              │                            │                         │
 │  [Loading状态]               │                            │                         │
 │                              │                            │                         │
 │                              │                   novel_preprocess                    │
 │                              │                            │───▶ 文本提取/分章        │
 │                              │                            │◀─── 结果返回             │
 │                              │                            │                         │
 │  WS: task_progress           │                            │                         │
 │  {step: "preprocess"}        │                            │                         │
 │◀────── WS 推送 ─────────────│◀─── WS publish ───────────│                         │
 │                              │                            │                         │
 │                              │                comprehensive_extraction                │
 │                              │                            │────── 发送 Prompt ──────▶│
 │                              │                            │◀───── 返回提取结果 ─────│
 │                              │                            │                         │
 │  WS: task_progress           │                            │                         │
 │  {step: "extraction"}        │                            │                         │
 │◀────── WS 推送 ─────────────│◀─── WS publish ───────────│                         │
 │                              │                            │                         │
 │                              │          串行: character → scene → prop → outline       │
 │                              │                            │────── 逐个串行调用 ────▶│
 │                              │                            │◀───── 逐个返回结果 ────│
 │                              │                            │                         │
 │  WS: task_progress           │                            │                         │
 │  {step: "character/..."}     │                            │                         │
 │◀────── WS 推送 ─────────────│◀─── WS publish ───────────│                         │
 │                              │                            │                         │
 │                              │                first_ep_storyboard_gen                 │
 │                              │                            │────── 发送 Prompt ──────▶│
 │                              │                            │◀───── 返回分镜 ─────────│
 │                              │                            │                         │
 │                              │                   汇总写入 PG                        │
 │                              │                            │ update version           │
 │                              │                            │ status→storyReady        │
 │                              │                            │                         │
 │  WS: analysis_completed      │                            │                         │
 │  {project_status:storyReady} │                            │                         │
 │◀────── WS 推送 ─────────────│◀─── WS publish ───────────│                         │
 │                              │                            │                         │
 │  [显示确认弹窗]              │                            │                         │
 │                              │                            │                         │
 │  PUT /projects/{id}/confirm  │                            │                         │
 │  {title, ratio, style}       │                            │                         │
 │─────────────────────────────▶│                            │                         │
 │                              │ status→projectCreated      │                         │
 │  {project}                   │                            │                         │
 │◀─────────────────────────────│                            │                         │
 │                              │                            │                         │
 │  GET /projects/{id}/analysis │                            │                         │
 │─────────────────────────────▶│                            │                         │
 │  {五部分数据}                │                            │                         │
 │◀─────────────────────────────│                            │                         │
 │                              │                            │                         │
 │  [展示分析结果]              │                            │                         │
```

### 7.2 调整时序

```
前端                         FastAPI                     Celery Worker              模型 API
 │                              │                            │                         │
 │  PUT /projects/{id}/analyze  │                            │                         │
 │  {adjustment: "让主角..."}   │                            │                         │
 │─────────────────────────────▶│                            │                         │
 │                              │ status→analyzingStory      │                         │
 │                              │ 创建 version v2            │                         │
 │                              │   (parent=v1)              │                         │
 │                              │ 提交 adjust task ──────────▶│                         │
 │  {task_id}                   │                            │                         │
 │◀─────────────────────────────│                            │                         │
 │                              │                            │                         │
 │  [Loading状态]               │                            │                         │
 │                              │                            │                         │
 │                              │                增量调整（单次模型调用）                │
 │                              │                            │                          │
 │                              │                            │ 构建 Prompt:             │
 │                              │                            │   context_snapshot       │
 │                              │                            │   + adjustment_history   │
 │                              │                            │   + user_instruction     │
 │                              │                            │────── 发送 ─────────────▶│
 │                              │                            │◀───── 返回修改结果 ─────│
 │                              │                            │                         │
 │                              │                            │ 合并到新版本             │
 │                              │                            │ 更新 adjustment_context  │
 │                              │                            │ status→projectCreated    │
 │                              │                            │                         │
 │  WS: adjustment_completed    │                            │                         │
 │◀────── WS 推送 ─────────────│◀─── WS publish ───────────│                         │
 │                              │                            │                         │
 │  GET /projects/{id}/analysis │                            │                         │
 │─────────────────────────────▶│                            │                         │
 │  {更新后的五部分数据}        │                            │                         │
 │◀─────────────────────────────│                            │                         │
```

---

## 八、WebSocket 事件设计

### 8.1 故事分析相关事件

| event_type | 触发时机 | data 结构 |
|------------|----------|-----------|
| `analysis_started` | 分析任务开始执行 | `{project_id, version_id, task_id}` |
| `analysis_progress` | 每个子任务完成 | `{project_id, step: "preprocess"\|"extraction"\|"layer2_start"\|"character"\|"scene"\|"prop"\|"outline"\|"storyboard"\|"adjustment_start"\|"adjustment_done", progress: 0-100}` |
| `analysis_completed` | 全部分析完成 | `{project_id, version_id, project_status: "storyReady"}` |
| `analysis_failed` | 分析失败 | `{project_id, error_message, retry_count}` |
| `adjustment_completed` | 调整完成 | `{project_id, version_id, project_status: "projectCreated"}` |
| `adjustment_failed` | 调整失败 | `{project_id, error_message}` |

### 8.2 前端处理逻辑

```javascript
// WebSocket 事件处理（伪代码）
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)

    switch (msg.event_type) {
        case 'analysis_completed':
            // 状态从 analyzingStory → storyReady
            // 弹出确认弹窗
            showConfirmDialog()
            break

        case 'analysis_progress':
            // 更新进度显示（可选：在 loading 下方显示进度文字）
            updateProgressText(msg.data.step, msg.data.progress)
            break

        case 'analysis_failed':
            // 显示错误提示，允许重试
            showError(msg.data.error_message)
            break

        case 'adjustment_completed':
            // 状态从 analyzingStory → projectCreated
            // 重新拉取分析结果并渲染
            fetchAnalysis(msg.data.project_id)
            break
    }
}
```

---

## 九、错误处理

### 9.1 错误场景与处理

| 场景 | 错误表现 | 处理方式 |
|------|----------|----------|
| 模型 API 超时 | 子任务超时 | Celery 重试（最多3次），WS 推送 `analysis_failed`，前端显示重试按钮 |
| 模型返回格式错误 | JSON 解析失败 | 重试1次，若仍失败则降级为提示模型返回异常，建议用户重新分析 |
| 小说文本过短 | < 20字符 | 前端拦截（按钮置灰），后端也做校验返回 400 |
| 小说文本过长 | 超出模型上下文 | 后端检测字数，超限时自动分块处理 |
| 分析期间用户关闭页面 | WS 断连 | 分析继续执行，用户重新进入时通过 REST API 获取当前状态 |
| 分析期间用户点击「发送」 | 重复触发 | 前端判断 status == analyzingStory 时「发送」按钮置灰 |
| 并发确认项目设置 | 多人同时提交 | 最后写入胜出，无冲突检测 |
| 用户手动编辑分镜后保存失败 | 网络异常 | 前端保留编辑内容，提示重试 |

### 9.2 重试策略

| 任务类型 | 超时 | 最大重试 | 退避间隔 |
|----------|------|----------|----------|
| novel_preprocess | 60s | 2 | 15s |
| comprehensive_extraction | 180s | 3 | 30s |
| character_gen / scene_gen / prop_gen | 90s | 3 | 30s |
| episode_outline_gen | 120s | 3 | 30s |
| first_ep_storyboard_gen | 120s | 3 | 30s |
| story_analysis_workflow | 600s | 1 | 60s（整个 workflow 只重试1次） |
| story_analysis_adjust | 300s | 2 | 30s |

---

## 十、文件处理

### 10.1 文件上传流程

```
前端                              FastAPI                      云存储
 │                                  │                            │
 │  选择 .txt/.docx 文件            │                            │
 │─────────────────────────────────▶│                            │
 │                                  │ 校验文件格式               │
 │                                  │ 提取纯文本                 │
 │                                  │   txt: 直接读取             │
 │                                  │   docx: python-docx 提取   │
 │                                  │                            │
 │                                  │ 上传原始文件 ──────────────▶│
 │                                  │                            │ 存储
 │                                  │◀─────── 返回 URL ──────────│
 │                                  │                            │
 │  {file_url, extracted_text,      │                            │
 │   char_count, format}            │                            │
 │◀─────────────────────────────────│                            │
 │                                  │                            │
 │  文本自动填入输入框              │                            │
```

### 10.2 DOCX 提取

```python
import docx

def extract_text_from_docx(file_bytes: bytes) -> str:
    """从 DOCX 文件提取纯文本"""
    doc = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)
```

---

## 十一、前端状态管理

### 11.1 Pinia Store 设计

```javascript
// stores/project.js
export const useProjectStore = defineStore('project', () => {
    const project = ref(null)           // 项目详情
    const analysis = ref(null)          // 当前分析结果
    const isLoading = ref(false)        // 分析中标记
    const currentVersion = ref(null)    // 当前版本信息

    // 计算属性
    const isAnalyzing = computed(() =>
        project.value?.status === 'analyzingStory'
    )
    const isStoryReady = computed(() =>
        project.value?.status === 'storyReady'
    )
    const canEdit = computed(() =>
        project.value?.status === 'projectCreated'
    )
    const canProceed = computed(() =>
        project.value?.status === 'projectCreated' &&
        analysis.value !== null
    )

    // 方法
    async function createProject(novelText, fileUrl) { ... }
    async function startAnalysis() { ... }
    async function adjustAnalysis(adjustment) { ... }
    async function confirmProject(title, ratio, style) { ... }
    async function fetchProject(projectId) { ... }
    async function fetchAnalysis(projectId) { ... }
    async function saveStoryboard(storyboard) { ... }

    return {
        project, analysis, isLoading, currentVersion,
        isAnalyzing, isStoryReady, canEdit, canProceed,
        createProject, startAnalysis, adjustAnalysis,
        confirmProject, fetchProject, fetchAnalysis, saveStoryboard,
    }
})
```

---

## 十二、与系统架构文档的关系

本文档是 [系统架构设计 v1.1](drama-production-architecture.md) 中「第四章 Workflow 设计」和「第五章 增量调整方案」的具体落地。对应关系：

| 系统架构章节 | 本文档对应章节 |
|-------------|---------------|
| 三、数据模型设计 | 四、数据模型变更 |
| 四、Workflow 设计 | 五、Celery 任务设计 |
| 五、增量调整方案 | 五.3 增量调整 Workflow |
| 六、任务可靠性保障 | 九、错误处理 |
| 七、实时通信方案 | 八、WebSocket 事件设计 |
| - | 三、API 设计（新增） |
| - | 六、Prompt 设计（新增） |
| - | 七、前后端交互时序（新增） |
| - | 十三、模型调用层架构设计（v1.1 新增） |
| - | 十四、模型配置链路设计（v1.1 新增） |

---

## 十三、模型调用层架构设计

> 版本 v1.1 新增 | 日期: 2026-05-20

### 13.1 当前问题

当前 `model_provider.py` 存在三个架构缺陷：

| # | 问题 | 影响 |
|---|------|------|
| 1 | **全局单例** — `get_text_model()` 使用固定 `settings.LLM_API_KEY`/`settings.LLM_BASE_URL` | 所有用户共享同一模型和密钥，无法按用户/项目切换 |
| 2 | **单 Provider** — 仅支持 OpenAI-compatible 接口 | 无法路由到国内模型（百炼、火山引擎、智谱、DeepSeek 等） |
| 3 | **未接入配置体系** — `story_analysis.py` 直接调用 `get_text_model()` | 完全绕过 `ConfigReader` 已有的用户/项目级配置 |

### 13.2 LiteLLM 引入方案

**决策：引入 LiteLLM（SDK 模式），替换当前 `TextModelProvider` 全局单例。**

#### 13.2.1 架构设计

```
┌──────────────────────────────────────────────────────────┐
│  story_analysis / ai_expand / assistant_platform（调用方） │
└──────────────────────┬───────────────────────────────────┘
                       │ 传入 model_key (如 "analysis_model")
                       ▼
┌──────────────────────────────────────────────────────────┐
│  ModelCaller（新，替换 TextModelProvider）                 │
│  1. 从 ConfigReader 获取 resolved config                  │
│  2. 解析 model_key → litellm model name + api_key        │
│  3. 调用 litellm.completion() / litellm.acompletion()    │
│  4. 统一记录日志到 Redis 缓冲 + 项目日志文件              │
│  5. 返回归一化的 ModelResult                              │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│  LiteLLM（SDK 模式，非 Proxy Server）                     │
│  统一路由到:                                              │
│    openai/    → OpenAI / 任意 OpenAI-compatible 端点      │
│    dashscope/ → 阿里百炼（通义千问）                       │
│    volcengine/ → 火山引擎（豆包）                          │
│    deepseek/  → DeepSeek                                  │
│    moonshot/  → 月之暗面                                   │
│    zai/       → 智谱 AI（GLM）                            │
│    自定义 provider → api_base + api_key                   │
└──────────────────────────────────────────────────────────┘
```

#### 13.2.2 设计要点

1. **SDK 模式**（非 Proxy Server）：直接在进程中调用，避免额外网络开销和部署复杂度
2. **模型名称格式**：使用 LiteLLM 的 provider 前缀，如 `dashscope/qwen-plus`、`volcengine/doubao-pro`、`openai/gpt-4o`
3. **自定义 Provider 支持**：`UserApiConfig.custom_providers` 中的自定义端点通过 `api_base` + `api_key` 参数传递
4. **日志保留**：保留现有日志双写机制（Redis 缓冲 `model_call_log_writer` + 项目日志 `ProjectLogger`）
5. **响应归一化**：LiteLLM 已将所有 Provider 响应归一化为 OpenAI 格式，`ModelResult` 接口保持不变

#### 13.2.3 优劣势

| 优势 | 劣势 |
|------|------|
| 100+ Provider 统一接口，切换模型只需改前缀 | 2026.3 遭遇供应链攻击，需锁定版本 ≥1.83.0 |
| 国内模型全覆盖（百炼/火山/智谱/月之暗面/DeepSeek） | import 速度较慢（~2-3s） |
| 内置 fallback/路由/负载均衡机制 | 社区反馈生产环境有内存泄漏风险，需监控 |
| 费用追踪、token 统一统计 | 额外依赖，增加攻击面 |
| 流式/非流式/function calling 均支持 | — |
| 与 LangGraph 有官方集成文档 | — |

#### 13.2.4 安全要求

- 锁定版本范围：`litellm>=1.83.0,<2.0.0`
- 仅使用 SDK 模式，**不部署 Proxy Server**
- 定期检查安全更新

### 13.3 LangGraph 可行性分析

#### 13.3.1 LangGraph 简介

LangGraph 是基于有向无环图（DAG）的 AI 工作流编排框架，核心概念：
- **State**：图中流转的共享数据结构
- **Node**：执行计算的函数
- **Edge**：节点间固定流转
- **Conditional Edge**：基于状态动态决定下一步走向
- **Checkpoint**：状态持久化，支持断点续跑

#### 13.3.2 对当前故事分析流程的价值评估

当前故事分析是一个**固定的线性 Pipeline**：

```
层0: novel_preprocess (文本拆分)
  ↓
层1: comprehensive_extraction (全量提取)
  ↓
层2: character_gen | scene_gen | prop_gen | episode_outline_gen  (可并发)
  ↓
层3: first_ep_storyboard (分镜生成)
```

| LangGraph 能力 | 对当前流程的价值 | 说明 |
|----------------|-----------------|------|
| 条件边/分支 | **低** | 当前流程无分支需求，增量调整也只有一条路径 |
| 并行节点 | **中** | 层2的4个任务天然可并行，但 Celery `chord` 已能解决 |
| 状态持久化/checkpoint | **中** | 可用于断点续跑，但 Celery + DB 已实现类似能力 |
| Human-in-the-loop | **低** | 分析流程是全自动的，无需人工介入节点 |
| 循环/重试 | **中** | 可用于 LLM 输出质量检查后自动重试，但逻辑简单 |
| 多 Agent 协作 | **高（未来）** | 角色一致性校验、跨集剧情连贯性检查等 Agent 场景 |

#### 13.3.3 引入 LangGraph 的问题

1. **与 Celery 职责重叠**：Celery 已承担任务编排（`chord`/`chain`/`group`）、重试、状态追踪。LangGraph 的 StateGraph 也是编排层，两者叠加会导致"谁在编排谁"的混乱
2. **Worker 中运行复杂度**：LangGraph 的 `graph.invoke()` 在 Celery Worker 中运行可行，但状态持久化需要额外引入 Redis/PG checkpointer
3. **学习成本**：团队需理解 State/Node/Edge/ConditionalEdge 等图概念，对线性流程投入产出比不高
4. **调试复杂度**：图结构比当前的顺序函数调用更难调试

#### 13.3.4 决策

**当前阶段不引入 LangGraph。** 理由：

- 故事分析是线性多步骤 Pipeline，不是需要循环/分支/多 Agent 协作的复杂工作流
- Celery + DB 已提供任务编排、重试、状态管理能力
- LangGraph 的核心价值（条件路由、循环、Human-in-the-loop）在当前场景用不上

**未来可考虑引入的时机：**
- 进入多 Agent 协作阶段（角色一致性校验 Agent、剧情连贯性审查 Agent）
- 需要动态决策工作流路径（如根据小说类型选择不同分析策略）
- 需要 Human-in-the-loop 审核节点（关键创作决策需用户确认）

---

## 十四、模型配置链路设计

> 版本 v1.1 新增 | 日期: 2026-05-20

### 14.1 配置层级

模型配置遵循三层优先级：**系统默认值 < 设置中心 < 项目配置**。

```
┌─────────────────────────────────────┐
│  系统默认值 (.env)                   │  ← LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME
│  优先级最低，仅作兜底                │
└──────────────────┬──────────────────┘
                   ↓ 被覆盖
┌─────────────────────────────────────┐
│  设置中心 (UserApiConfig)            │  ← 用户级 API Key、模型选择、并发限制
│  用户在「设置中心」页面配置           │
│  包含: analysis_model, character_    │
│  model, custom_providers, 各平台     │
│  API Key 等                         │
└──────────────────┬──────────────────┘
                   ↓ 被覆盖
┌─────────────────────────────────────┐
│  项目配置 (project.config)           │  ← 单个项目可覆盖设置中心的模型选择
│  用户在项目设置中指定特定模型         │
│  仅覆盖可覆盖字段                    │
└──────────────────┬──────────────────┘
                   ↓ 解析为
┌─────────────────────────────────────┐
│  ResolvedConfig                     │
│  ConfigReader.get_project_config()  │
│  合并三层配置，解密所有 API Key       │
└─────────────────────────────────────┘
```

`ConfigReader.get_project_config(user_id, project.config)` 已实现三层合并逻辑，`_PROJECT_OVERRIDABLE_KEYS` 包含所有可被项目覆盖的模型字段。

### 14.2 故事分析流程的模型选择

故事分析的每个步骤应使用配置中对应的模型字段：

| 分析步骤 | 配置字段 | 说明 |
|---------|----------|------|
| `comprehensive_extraction` | `resolved.analysis_model` | 核心提取步骤，使用分析模型 |
| `character_gen` | `resolved.character_model` | 角色润色 |
| `scene_gen` | `resolved.location_model` | 场景润色 |
| `prop_gen` | `resolved.character_model` | 道具润色，复用角色模型 |
| `episode_outline_gen` | `resolved.analysis_model` | 大纲生成，复用分析模型 |
| `first_ep_storyboard` | `resolved.storyboard_model` | 分镜生成 |
| `story_analysis_adjust` | `resolved.analysis_model` | 增量调整，复用分析模型 |

**当前缺陷**：`story_analysis.py` 中所有 LLM 调用使用 `get_text_model()`（全局单例），**完全绕过了用户/项目配置**。需修正为通过 `ConfigReader` 获取配置后按任务类型选择对应模型。

### 14.3 Celery 任务中的配置传递

Celery Worker 无法直接访问 DB session，配置需要在触发任务时解析并序列化传入。

#### 14.3.1 触发时解析配置

```python
# API 端点中：触发分析时解析配置
config_reader = ConfigReader(db)
resolved = config_reader.get_project_config(user_id, project.config)
model_config = resolved.to_dict()  # 序列化配置快照

# 提交 Celery 任务时传入配置快照
story_analysis_workflow.delay(
    project_id=str(project.id),
    user_id=str(user_id),
    model_config=model_config,
)
```

#### 14.3.2 Worker 中使用配置

```python
# Celery Worker 中：从配置快照创建 ModelCaller
@shared_task
def story_analysis_workflow(project_id, user_id, model_config):
    caller = ModelCaller.from_config_snapshot(model_config)

    # 层1: 使用分析模型
    extraction_result = caller.call(
        model_key="analysis_model",
        prompt=comprehensive_extraction_prompt,
        ...
    )

    # 层2: 各步骤使用对应模型
    character_result = caller.call(
        model_key="character_model",
        prompt=character_gen_prompt,
        ...
    )
    ...
```

#### 14.3.3 配置快照持久化

每次分析时将使用的模型配置快照写入 `AnalysisVersion.model_config_data`，确保：
- 可追溯每次分析使用的具体模型和参数
- 即使设置中心/项目配置后续变更，历史分析的配置记录不变
- 支持按模型统计 token 消耗和费用

### 14.4 ModelCaller 接口设计

`ModelCaller` 替换当前的 `TextModelProvider`，支持多 Provider 路由和配置驱动：

```python
class ModelCaller:
    """配置驱动的模型调用器，替换 TextModelProvider"""

    def __init__(self, resolved_config: ResolvedConfig):
        self.config = resolved_config

    @classmethod
    def from_config_snapshot(cls, config_dict: dict) -> "ModelCaller":
        """从序列化的配置快照创建实例（供 Celery Worker 使用）"""
        resolved = ResolvedConfig(**config_dict)
        return cls(resolved)

    def call(
        self,
        model_key: str,            # "analysis_model" / "character_model" / ...
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        timeout: int = 180,
        project_id: str = None,
        task_id: str = None,
    ) -> ModelResult:
        """
        根据配置调用对应模型

        1. 从 config 中获取 model_key 对应的模型名（含 provider 前缀）
        2. 解析出 provider，获取对应的 API Key
        3. 调用 litellm.completion()，传入 model / api_key / api_base
        4. 记录日志到 Redis 缓冲 + 项目日志
        5. 返回归一化的 ModelResult
        """
        ...
```

### 14.5 配置缺失时的降级策略

| 场景 | 处理方式 |
|------|----------|
| 用户未配置设置中心 | 使用系统默认值（`settings.LLM_API_KEY` + `settings.LLM_MODEL_NAME`） |
| 项目配置中某个模型字段为空 | 回退到设置中心同字段，若仍为空则使用 `analysis_model` |
| API Key 解密失败 | 记录警告日志，回退到系统默认 API Key |
| 自定义 Provider 端点不可达 | 抛出异常，Celery 重试，WS 推送 `analysis_failed` |
