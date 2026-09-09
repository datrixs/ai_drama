# 短剧制作系统 — 技术架构设计

> 版本: v1.1 | 日期: 2026-05-18 | 作者: 架构师

---

## 一、补充设计点与风险分析

### 1.1 设计点

| # | 设计点 | 说明 |
|---|--------|------|
| 1 | **小说预处理与分章** | 用户上传格式限定 TXT/DOCX 两种，后端统一提取纯文本并按章节拆分，章节是后续生成"每集剧本大纲"的输入单元 |
| 2 | **生成内容版本管理** | 每次调整/重新生成都会产生新的内容版本，需要版本链路追踪——哪次调整改了什么、基于哪个版本 |
| 3 | **上下文窗口限制** | 长篇小说可能超出模型上下文窗口，需要分块策略和摘要拼接 |
| 4 | **模型调用配额与限流** | 外部模型 API 有速率限制和费用上限，需要按用户/项目做配额管理和限流 |
| 5 | **资产分级与复用** | 资产分为全局资产（人物/场景/道具/音频）和项目资产（人物/场景/道具），全局资产可跨项目复用 |
| 6 | **分镜与视频的时长/分辨率约束** | 不同视频模型对输入有格式要求（分镜描述长度、图片尺寸），需要适配层 |
| 7 | **用户断线重连** | WebSocket 断连后客户端需能恢复到当前流程状态，不丢失进度 |
| 8 | **项目级隔离** | 日志、存储路径按项目隔离，支持按项目下载日志 |
| 9 | **多模型切换与回退** | 文本/图片/视频模型可能需要切换供应商，需抽象模型调用层，支持故障转移 |
| 10 | **ORM 确认** | 后端统一使用 SQLAlchemy ORM，不使用 SQLModel |

### 1.2 风险与问题

| # | 风险 | 影响 | 缓解措施 |
|---|------|------|----------|
| R1 | **模型 API 不稳定** | 任务卡住或失败 | 重试机制 + 超时检测 + 备用模型回退 |
| R2 | **长文本超出上下文** | 生成内容截断或质量下降 | 分块摘要 + 分阶段处理 |
| R3 | **调整时全量重传小说** | token 成本高、延迟大 | 增量上下文方案（详见第五章） |
| R4 | **并发任务资源竞争** | Redis/DB 连接池耗尽、模型 API 限流 | 连接池监控 + 令牌桶限流 + 任务优先级队列 |
| R5 | **Celery Worker 单点** | Worker 挂掉任务丢失 | 持久化队列(Redis) + 任务结果后端(PG) + 健康检查 |
| R6 | **WebSocket 连接风暴** | 大量用户同时在线时连接数过多 | 连接数上限 + 心跳检测 + Redis 消息缓冲（详见第七章） |
| R7 | **生成内容一致性** | 并发生成各子项时，人物描述与场景描述可能矛盾 | 第一阶段串行生成全局设定，第二阶段才并发 |
| R8 | **存储成本** | 大量图片/视频占用云存储 | 生命周期策略 + 冷热分层存储 |
| R9 | **高频日志写入性能** | 模型调用日志量大，写入 PG 影响业务库性能 | 分区表 + Redis 缓冲批量写入（详见第八章） |
| R10 | **task_record 表膨胀** | 任务记录持续增长，查询变慢 | 按月分区 + 历史归档（详见第八章） |

---

## 二、系统整体架构

### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Vue3 前端 (SPA)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 剧情分析  │ │ 资产库   │ │ 剧集制作  │ │ 项目管理  │ │ 系统配置  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│       └────────────┴────────────┴────────────┴────────────┘        │
│                            │ REST API + WebSocket                   │
└────────────────────────────┼────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────┐
│                     FastAPI 网关层                                   │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐                 │
│  │ 认证/鉴权    │ │ 限流/配额     │ │ 请求路由      │                 │
│  └─────────────┘ └──────────────┘ └──────────────┘                 │
│                            │                                        │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐                 │
│  │ 项目管理 API │ │ 任务管理 API  │ │ 资产管理 API  │                 │
│  └──────┬──────┘ └──────┬───────┘ └──────┬───────┘                 │
└─────────┼───────────────┼───────────────┼───────────────────────────┘
          │               │               │
          ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      业务服务层                                      │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐             │
│  │ 剧情分析服务   │ │ 资产生成服务   │ │ 剧集制作服务   │             │
│  │(Workflow引擎) │ │(图片生成)      │ │(视频生成)      │             │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘             │
│          │                 │                 │                      │
│  ┌───────┴───────┐ ┌───────┴───────┐ ┌───────┴───────┐             │
│  │ 模型调用抽象层 │ │ 模型调用抽象层 │ │ 模型调用抽象层 │             │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘             │
└──────────┼─────────────────┼─────────────────┼──────────────────────┘
           │                 │                 │
           ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      任务调度层 (Celery)                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ 文本任务  │ │ 图片任务  │ │ 视频任务  │ │ 定时检测  │              │
│  │ Worker   │ │ Worker   │ │ Worker   │ │ Beat     │              │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘              │
└───────┼────────────┼────────────┼────────────┼──────────────────────┘
        │            │            │            │
        ▼            ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────────┐
│  PostgreSQL   │ │    Redis     │ │         云存储 (MinIO/OSS)       │
│ ┌──────────┐ │ │ ┌──────────┐ │ │  ┌────────┐ ┌────────┐ ┌─────┐ │
│ │ 业务数据  │ │ │ │ 任务队列  │ │ │  │ 图片   │ │ 视频   │ │ 日志│ │
│ │ 任务记录  │ │ │ │ 结果缓存  │ │ │  └────────┘ └────────┘ └─────┘ │
│ │ 版本记录  │ │ │ │ WS消息缓冲│ │ │                                  │
│ │ 模型日志  │ │ │ │ 限流令牌   │ │ │                                  │
│ └──────────┘ │ │ └──────────┘ │ │                                  │
└──────────────┘ └──────────────┘ └──────────────────────────────────┘
```

### 2.2 核心设计原则

1. **异步非阻塞**: FastAPI 异步处理 HTTP 请求，耗时模型调用全部下沉到 Celery Worker
2. **任务持久化**: 所有任务状态写入 PG，Redis 仅做队列和缓存，服务重启后从 PG 恢复
3. **幂等执行**: 任务通过唯一 ID 去重，同一任务不会并行执行
4. **增量上下文**: 调整时只传递差异，不重复传输全量小说
5. **项目隔离**: 日志、存储路径均按项目 ID 隔离
6. **ORM 统一**: 全部使用 SQLAlchemy ORM，不使用 SQLModel

---

## 三、数据模型设计

### 3.1 核心实体关系
```
中英文术语对照
场景‌：Scene
道具‌：Prop
人物/角色‌：Character
分镜‌：Storyboard
视频片段‌：Clip
剧本‌：Script
剧集‌：Episode
```

```
Project 1──N Episode
Project 1──1 AnalysisResult
Project 1──N ProjectCharacter (人物)
Project 1──N ProjectLocation  (场景)
Project 1──N ProjectProp      (道具)
Project 1──N OperationRecord

User ──1:N── GlobalAssetFolder (资产文件夹)
User ──1:N── GlobalCharacter (全局人物)
User ──1:N── GlobalLocation  (全局场景)
User ──1:N── GlobalProp      (全局道具)
User ──1:N── GlobalVoice     (全局音色)

AnalysisResult 1──N AnalysisVersion
AnalysisVersion 包含: 全局设定 + 各集大纲 + 第一集分镜

Episode 1──N Storyboard
Storyboard 1──N VideoClip
```

### 3.2 公共审计字段

所有业务表继承以下审计字段，ORM 中通过 BaseMixin 自动提供：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(32) | 主键，雪花 ID |
| create_time | DateTime | 创建时间，NOT NULL |
| creator | String(32) | 创建人 ID |
| update_time | DateTime | 最近修改时间 |
| modifier | String(32) | 最近修改人 ID |
| is_deleted | Boolean | 逻辑删除标记，默认 FALSE |

### 3.3 核心表结构

```sql
-- ============================================================
-- 项目
-- ============================================================
CREATE TABLE project (
    id              VARCHAR(32) PRIMARY KEY,
    user_id         VARCHAR(32) NOT NULL,
    title           VARCHAR(256),
    novel_text      TEXT,
    novel_meta      JSONB,                   -- {章节数, 字数, 格式, 文件名}
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',  -- draft/analyzing/assets_ready/producing/completed
    phase           VARCHAR(32),             -- text_analysis/image_generation/video_production
    last_access_time                         -- 最近访问时间
    ...                                          -- 审计字段
);

CREATE INDEX idx_project_user_id ON project(user_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_project_status ON project(status) WHERE is_deleted = FALSE;

-- ============================================================
-- 分析结果（一个项目一条，记录当前确认的版本）
-- ============================================================
CREATE TABLE analysis_result (
    id                  VARCHAR(32) PRIMARY KEY,
    project_id          VARCHAR(32) NOT NULL REFERENCES project(id),
    current_version_id  VARCHAR(32),
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/generating/completed
    ...
);

-- ============================================================
-- 分析版本（每次生成/调整产生新版本）
-- ============================================================
CREATE TABLE analysis_version (
    id                      VARCHAR(32) PRIMARY KEY,
    analysis_result_id      VARCHAR(32) NOT NULL REFERENCES analysis_result(id),
    parent_version_id       VARCHAR(32),                 -- 基于哪个版本调整
    version_number          INTEGER NOT NULL,

    -- 全局设定（串行生成，所有子项共享）
    global_setting          JSONB,                       -- {故事概要, 世界观, 风格基调, 人物关系图谱, 人物列表, 场景列表, 道具列表}

    -- 各子项（并发生成）
    character_profiles      JSONB,                       -- 人物特征列表
    scene_descriptions      JSONB,                       -- 场景描写列表
    prop_descriptions       JSONB,                       -- 道具描写列表
    episode_outlines        JSONB,                       -- 每集剧本大纲
    first_ep_storyboard     JSONB,                       -- 第一集分镜

    -- 增量调整上下文
    adjustment_context      JSONB,                       -- {摘要, 关键设定, 历史调整链}

    prompt_snapshot         TEXT,
    model_config            JSONB,
    token_usage             JSONB,

    is_confirmed            BOOLEAN NOT NULL DEFAULT FALSE,
    ...
);

-- ============================================================
-- 项目人物（每个项目可有多个角色）
-- ============================================================
CREATE TABLE project_character (
    id                      VARCHAR(32) PRIMARY KEY,
    project_id              VARCHAR(32) NOT NULL REFERENCES project(id),
    name                    VARCHAR(256) NOT NULL,
    aliases                 TEXT,                       -- 别名/曾用名
    description             TEXT,                       -- AI 生成的人物描述（可由用户修改）
    profile_data            JSONB,                      -- 角色设定 {性格, 背景, 行为特征, ...}
    profile_confirmed       BOOLEAN NOT NULL DEFAULT FALSE,
    voice_id                VARCHAR(128),               -- 绑定的音色 ID
    voice_type              VARCHAR(64),                -- 音色类型
    custom_voice_url        VARCHAR(1024),              -- 自定义音色文件 URL
    image_url               VARCHAR(1024),              -- 当前图片 URL
    image_prompt            TEXT,                       -- 图片生成提示词（可由用户修改后重新生成）
    gen_status              VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/generating/completed/failed
    source_global_id        VARCHAR(32),                -- 从全局角色复制来源
    ...
);

CREATE INDEX idx_project_character_project ON project_character(project_id) WHERE is_deleted = FALSE;

-- ============================================================
-- 项目场景（每个项目可有多个场景）
-- ============================================================
CREATE TABLE project_location (
    id                      VARCHAR(32) PRIMARY KEY,
    project_id              VARCHAR(32) NOT NULL REFERENCES project(id),
    name                    VARCHAR(256) NOT NULL,
    summary                 TEXT,                       -- 场景摘要（来自分析结果）
    description             TEXT,                       -- 场景图片描述（可由用户修改）
    image_url               VARCHAR(1024),              -- 当前图片 URL
    image_prompt            TEXT,                       -- 图片生成提示词（可由用户修改后重新生成）
    gen_status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    source_global_id        VARCHAR(32),                -- 从全局场景复制来源
    ...
);

CREATE INDEX idx_project_location_project ON project_location(project_id) WHERE is_deleted = FALSE;

-- ============================================================
-- 项目道具（每个项目可有多个道具）
-- ============================================================
CREATE TABLE project_prop (
    id                      VARCHAR(32) PRIMARY KEY,
    project_id              VARCHAR(32) NOT NULL REFERENCES project(id),
    name                    VARCHAR(256) NOT NULL,
    description             TEXT,                       -- AI 生成的道具描述（可由用户修改）
    image_url               VARCHAR(1024),              -- 当前图片 URL
    image_prompt            TEXT,                       -- 图片生成提示词（可由用户修改后重新生成）
    gen_status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    source_global_id        VARCHAR(32),                -- 从全局道具复制来源
    ...
);

CREATE INDEX idx_project_prop_project ON project_prop(project_id) WHERE is_deleted = FALSE;

-- ============================================================
-- 全局人物（跨项目复用）
-- ============================================================
CREATE TABLE global_character (
    id                      VARCHAR(32) PRIMARY KEY,
    user_id                 VARCHAR(32) NOT NULL,
    folder_id               VARCHAR(32),                -- 资产文件夹
    name                    VARCHAR(256) NOT NULL,
    aliases                 TEXT,
    description             TEXT,
    profile_data            JSONB,
    profile_confirmed       BOOLEAN NOT NULL DEFAULT FALSE,
    voice_id                VARCHAR(128),
    voice_type              VARCHAR(64),
    custom_voice_url        VARCHAR(1024),
    image_url               VARCHAR(1024),              -- 当前图片 URL
    create_time             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator                 VARCHAR(32),
    update_time             TIMESTAMPTZ,
    modifier                VARCHAR(32),
    is_deleted              BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- 全局场景（跨项目复用）
-- ============================================================
CREATE TABLE global_location (
    id                      VARCHAR(32) PRIMARY KEY,
    user_id                 VARCHAR(32) NOT NULL,
    folder_id               VARCHAR(32),
    name                    VARCHAR(256) NOT NULL,
    summary                 TEXT,
    description             TEXT,
    image_url               VARCHAR(1024),
    create_time             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator                 VARCHAR(32),
    update_time             TIMESTAMPTZ,
    modifier                VARCHAR(32),
    is_deleted              BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- 全局道具（跨项目复用）
-- ============================================================
CREATE TABLE global_prop (
    id                      VARCHAR(32) PRIMARY KEY,
    user_id                 VARCHAR(32) NOT NULL,
    folder_id               VARCHAR(32),
    name                    VARCHAR(256) NOT NULL,
    description             TEXT,
    image_url               VARCHAR(1024),
    create_time             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator                 VARCHAR(32),
    update_time             TIMESTAMPTZ,
    modifier                VARCHAR(32),
    is_deleted              BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- 全局音色
-- ============================================================
CREATE TABLE global_voice (
    id                      VARCHAR(32) PRIMARY KEY,
    user_id                 VARCHAR(32) NOT NULL,
    folder_id               VARCHAR(32),
    name                    VARCHAR(256) NOT NULL,
    description             TEXT,
    voice_id                VARCHAR(128),
    voice_type              VARCHAR(64) NOT NULL DEFAULT 'qwen-designed',
    custom_voice_url        VARCHAR(1024),
    voice_prompt            TEXT,                       -- 音色设计提示词
    gender                  VARCHAR(16),
    language                VARCHAR(16) NOT NULL DEFAULT 'zh',
    create_time             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator                 VARCHAR(32),
    update_time             TIMESTAMPTZ,
    modifier                VARCHAR(32),
    is_deleted              BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- 资产文件夹（全局资产分类管理）
-- ============================================================
CREATE TABLE global_asset_folder (
    id                      VARCHAR(32) PRIMARY KEY,
    user_id                 VARCHAR(32) NOT NULL,
    name                    VARCHAR(256) NOT NULL,
    create_time             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator                 VARCHAR(32),
    update_time             TIMESTAMPTZ,
    modifier                VARCHAR(32),
    is_deleted              BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- 剧集
-- ============================================================
CREATE TABLE episode (
    id              VARCHAR(32) PRIMARY KEY,
    project_id      VARCHAR(32) NOT NULL REFERENCES project(id),
    episode_number  INTEGER NOT NULL,
    name            VARCHAR(256) # 剧集名称
    outline         TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/storyboard_ready/video_ready/completed
    ...
);

-- ============================================================
-- 分镜
-- ============================================================
CREATE TABLE storyboard (
    id              VARCHAR(32) PRIMARY KEY,
    episode_id      VARCHAR(32) NOT NULL REFERENCES episode(id),
    shot_number     INTEGER NOT NULL,
    description     TEXT,
    reference_image VARCHAR(1024),
    duration        FLOAT,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/video_generating/completed
    create_time     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator         VARCHAR(32),
    update_time     TIMESTAMPTZ,
    modifier        VARCHAR(32),
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- 视频片段
-- ============================================================
CREATE TABLE video_clip (
    id              VARCHAR(32) PRIMARY KEY,
    storyboard_id   VARCHAR(32) NOT NULL REFERENCES storyboard(id),
    video_url       VARCHAR(1024),
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/generating/completed/failed
    create_time     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator         VARCHAR(32),
    update_time     TIMESTAMPTZ,
    modifier        VARCHAR(32),
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- 任务记录（按月分区，详见 8.3）
-- ============================================================
CREATE TABLE task_record (
    id              VARCHAR(32) PRIMARY KEY,
    project_id      VARCHAR(32) NOT NULL,
    task_type       VARCHAR(64) NOT NULL,    -- text_analysis/character_gen/scene_gen/...
    celery_task_id  VARCHAR(256),
    parent_task_id  VARCHAR(32),

    status          VARCHAR(32) NOT NULL DEFAULT 'pending',  -- pending/running/success/failed/timeout/cancelled
    worker_id       VARCHAR(256),

    input_params    JSONB,
    output_result   JSONB,

    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    next_retry_at   TIMESTAMPTZ,

    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    timeout_at      TIMESTAMPTZ,

    error_message   TEXT,
    create_time     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator         VARCHAR(32),
    update_time     TIMESTAMPTZ,
    modifier        VARCHAR(32),
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE
) PARTITION BY RANGE (create_time);

-- 按月分区（示例，Alembic 迁移中自动创建未来月份分区）
CREATE TABLE task_record_2026_05 PARTITION OF task_record
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE task_record_2026_06 PARTITION OF task_record
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE INDEX idx_task_record_project ON task_record(project_id);
CREATE INDEX idx_task_record_status ON task_record(status) WHERE is_deleted = FALSE;
CREATE INDEX idx_task_record_timeout ON task_record(timeout_at) WHERE status = 'running';

-- ============================================================
-- 模型调用日志（按月分区，详见 8.2）
-- ============================================================
CREATE TABLE model_call_log (
    id              VARCHAR(32) PRIMARY KEY,
    user_id         VARCHAR(32) NOT NULL,
    project_id      VARCHAR(32),
    task_id         VARCHAR(32),

    request_id      VARCHAR(128) NOT NULL,   -- 调用端生成的唯一请求 ID
    model_provider  VARCHAR(64) NOT NULL,    -- openai/anthropic/zhipu/...
    model_name      VARCHAR(128) NOT NULL,   -- gpt-4o/claude-3-opus/...
    endpoint        VARCHAR(512) NOT NULL,   -- API 端点 URL
    api_key_masked  VARCHAR(64),             -- 脱敏后的 API Key (sk-***abc)

    request_body    JSONB,                   -- 请求体（不含 API Key）
    response_status INTEGER,                 -- HTTP 状态码
    response_body   JSONB,                   -- 响应体摘要

    input_tokens    INTEGER,
    output_tokens   INTEGER,
    total_tokens    INTEGER,
    latency_ms      INTEGER,                 -- 调用耗时(毫秒)

    is_retry        BOOLEAN NOT NULL DEFAULT FALSE,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,

    create_time     TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (create_time);

-- 按月分区
CREATE TABLE model_call_log_2026_05 PARTITION OF model_call_log
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE model_call_log_2026_06 PARTITION OF model_call_log
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE INDEX idx_model_call_log_user ON model_call_log(user_id);
CREATE INDEX idx_model_call_log_project ON model_call_log(project_id);
CREATE INDEX idx_model_call_log_task ON model_call_log(task_id);
CREATE INDEX idx_model_call_log_provider ON model_call_log(model_provider, model_name);
CREATE INDEX idx_model_call_log_time ON model_call_log(create_time);

-- ============================================================
-- 操作记录（关键业务操作，供前端展示，区别于日志文件）
-- ============================================================
CREATE TABLE operation_record (
    id              VARCHAR(32) PRIMARY KEY,
    project_id      VARCHAR(32) NOT NULL,
    user_id         VARCHAR(32) NOT NULL,
    action          VARCHAR(64) NOT NULL,    -- create_project/upload_novel/start_analysis/adjust/confirm/...
    target_type     VARCHAR(32),             -- project/analysis_version/asset/episode/...
    target_id       VARCHAR(32),
    detail          JSONB,                   -- 操作详情
    create_time     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    creator         VARCHAR(32)
);

CREATE INDEX idx_operation_record_project ON operation_record(project_id);
```

### 3.4 资产表分表设计的理由

**为什么按人物/场景/道具分表而非使用 `asset_type` 区分**：

| 维度 | 人物 (Character) | 场景 (Location) | 道具 (Prop) |
|------|-------------------|-----------------|-------------|
| 独有字段 | `aliases`, `profile_data`, `voice_id`, `voice_type`, `custom_voice_url` | `summary` | — |
| 业务逻辑 | 音色绑定、角色设定确认 | 场景摘要 | 外观描述 |
| 查询模式 | 需带音色信息 | 关注摘要 | 关注描述 |

合并成一张表的代价：大量 nullable 类型专属字段 + `WHERE asset_type = 'character'` 过滤。分表后每种资产独立的 CRUD / Service / Schema，代码更清晰。

**图片存储策略（v1.0）**：

每资产一张图，`image_url` / `image_prompt` / `gen_status` 直接存在主表上，无独立图片子表。重新生成时直接覆盖旧图。查询无需 JOIN。

**用户修改图片流程**：
1. 用户修改 `description` 或 `image_prompt` → 前端自动保存到主表
2. 用户点击「重新生成」→ `gen_status` 置为 `generating`，触发 Celery 任务
3. 任务完成 → 更新 `image_url`，`gen_status` → `completed`

**全局 vs 项目资产**：

| 维度 | 全局资产 | 项目资产 |
|------|---------|---------|
| 归属 | 用户级（`user_id`），跨项目复用 | 项目级（`project_id`），项目内独立 |
| 类型 | character / location / prop / **voice** | character / location / prop |
| 生命周期 | 独立于项目存在 | 随项目创建/删除 |
| 图片 | `image_url`（用户上传/手动管理） | `image_url` + `image_prompt` + `gen_status`（AI 生成流程驱动） |
| 文件夹 | `folder_id` 支持分类 | 无 |

**项目资产引入全局资产**：通过 `source_global_id` 记录来源，引入时复制描述和图片到项目资产，后续项目内独立修改。

---

## 四、Workflow 设计：剧情分析流程

### 4.1 Workflow 流程图

> **核心原则**：Layer 1 是唯一接触完整小说的环节，必须做详尽提取。
> Layer 2 不接触原文，只做格式化润色——将提取的原始细节组织成适合图片生成的描写。
> 详细设计见 [story-analysis-detail-design.md](story-analysis-detail-design.md)

```
用户输入/上传小说 (TXT/DOCX)
        │
        ▼
┌───────────────────┐
│ Step 0: 小说预处理  │  提取纯文本、分章、元信息提取
│ (Celery Task)      │  输出: novel_text, chapters[], novel_meta
└────────┬──────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────┐
│ Step 1: 详尽提取 (串行, 唯一接触完整小说的步骤)              │
│                                                             │
│ 输入: 完整小说文本 + novel_meta                              │
│ 模型调用: 文本模型(长上下文, 需要 180s 超时)                  │
│ 输出: {                                                     │
│   novel_summary,     // 故事概要                             │
│   world_setting,     // 世界观                               │
│   style_tone,        // 风格基调                             │
│   character_relations,// 人物关系                             │
│   character_details, // ★ 详尽的人物外貌/性格/行为提取         │
│   scene_details,     // ★ 详尽的场景感官细节提取               │
│   prop_details,      // ★ 详尽的道具外观细节提取               │
│   chapter_summaries, // 各章摘要                             │
│   episode_mapping    // 集数映射建议                         │
│ }                                                           │
│                                                             │
│ ★ 这是保留小说原始细节的关键步骤                              │
│ ★ 提取结果 + 小说摘要 存入 adjustment_context               │
└────────┬──────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────────────────────┐
│ Step 2: 格式化润色 (并发, 基于提取结果, 不接触原文)           │
│                                                             │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ 2a: 人物特征  │ │ 2b: 场景描写  │ │ 2c: 道具描写  │        │
│ │  格式化润色   │ │  格式化润色   │ │  格式化润色   │        │
│ │              │ │              │ │              │        │
│ │ 输入:        │ │ 输入:        │ │ 输入:        │        │
│ │ char_details │ │ scene_details│ │ prop_details │        │
│ │ + char_rel.  │ │              │ │              │        │
│ │              │ │              │ │              │        │
│ │ 输出:        │ │ 输出:        │ │ 输出:        │        │
│ │ 标准化描写   │ │ 标准化描写   │ │ 标准化描写   │        │
│ │ + 图片prompt │ │ + 图片prompt │ │ + 图片prompt │        │
│ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘        │
│        │                │                │                 │
│ ┌──────┴───────┐ ┌──────┴────────────────┴───────┐        │
│ │ 2d: 每集大纲  │ │ 2e: 第一集分镜                  │        │
│ │              │ │                                │        │
│ │ 输入:        │ │ 输入:                          │        │
│ │ novel_summary│ │ novel_summary                  │        │
│ │ + char_rel.  │ │ + 第1集大纲(2d结果)             │        │
│ │ + chap_summ. │ │ + 人物特征(2a结果)              │        │
│ │ + ep_mapping │ │ + 场景描写(2b结果)              │        │
│ │              │ │ + 角色原始细节                   │        │
│ └──────┬───────┘ └──────────────┬─────────────────┘        │
│        │                       │                           │
│        └─────── 并发执行 ───────┘                           │
│        │  注: 2e 依赖 2a/2b/2d，需等它们完成                │
└────────┬──────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────────┐
│ Step 3: 结果汇总与版本记录  │
│ 合并所有子项 → 保存为       │
│ analysis_version v1        │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐     ┌──────────────────────┐
│ Step 4: 用户审阅           │────▶│ 用户不满意,输入调整    │
│ WS 推送生成完成通知         │     │ 提示词               │
└───────────────────────────┘     └──────────┬───────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │ Step 5: 增量调整       │
                                  │ (详见第五章)           │
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                  回到 Step 4 (用户审阅)
```

### 4.2 子项并发拆分分析

**结论: 推荐拆分，但采用分层依赖的并发策略**

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|------|
| 全串行 | 实现简单，一致性最强 | 速度慢，总耗时 = 各子项之和 | 否 |
| 全并发 | 速度最快 | 各子项之间缺乏一致性约束（人物特征可能与场景描写矛盾） | 否 |
| **分层依赖并发** | 速度较快（串行1步+并发1步），全局设定保证一致性 | 实现稍复杂 | **是** |

**分层依赖并发策略：**

```
Layer 0 (串行):  详尽提取 ← 唯一接触完整小说的步骤，提取所有原始细节
Layer 1 (并发):  人物特征(2a) + 场景描写(2b) + 道具描写(2c) + 每集大纲(2d)
                 ↑ 基于 Layer 0 的提取结果做格式化润色，不接触原文
Layer 2 (串行):  第一集分镜(2e) ← 依赖 2a/2b/2d 结果
```

- Layer 0 是保留小说原始细节的关键步骤，输出包含原文级的视觉描写提取
- Layer 1 各子任务基于提取结果做格式化润色，生成适合图片生成的标准化描写 + 英文 prompt
- 第一集分镜需要引用具体的人物特征和场景描写，必须等 2a/2b/2d 完成
- 2a/2b/2c/2d 之间无依赖，可并发执行

---

## 五、增量调整方案（核心难点）

### 5.1 问题分析

用户对生成结果不满意时输入调整提示词，如果每次都将完整小说重传给模型：

- **成本高**: 一部 10 万字小说 ≈ 13 万 token 输入，每次调整都重传
- **速度慢**: 长上下文输入导致模型推理延迟大
- **体验差**: 用户只是想调整"主角性格再硬朗一些"，却要等 2-3 分钟

### 5.2 方案设计: 结构化增量上下文 + 专注调整

**核心思想**: 首次分析时构建结构化上下文快照，后续调整只传递"当前状态 + 调整指令"，不再重传原始小说。

```
┌─────────────────────────────────────────────────────────────────┐
│                    增量调整架构                                    │
│                                                                   │
│  首次生成:                                                        │
│  ┌──────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │ 完整小说  │───▶│ Step1: 全局设定    │───▶│ 构建上下文快照    │   │
│  │ (全量)    │    │ Step2: 并发生成    │    │ ContextSnapshot  │   │
│  └──────────┘    └──────────────────┘    └────────┬─────────┘   │
│                                                    │              │
│  后续调整:                                          ▼              │
│  ┌──────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │ 调整提示词│───▶│ 增量调整 Prompt   │───▶│ 模型生成新版本    │   │
│  │ (增量)   │    │ (无需小说原文)    │    │                  │   │
│  └──────────┘    └──────────────────┘    └──────────────────┘   │
│                                                                   │
│  ContextSnapshot 结构:                                            │
│  {                                                                │
│    "novel_summary": "故事概要(500-1000字)",                       │
│    "world_setting": "世界观描述",                                  │
│    "style_tone": "风格基调",                                      │
│    "character_relations": "人物关系图谱",                          │
│    "current_character_profiles": [...],  // 当前人物特征           │
│    "current_scene_descriptions": [...],  // 当前场景描写           │
│    "current_prop_descriptions": [...],   // 当前道具描写           │
│    "current_episode_outlines": [...],    // 当前每集大纲           │
│    "current_first_ep_storyboard": [...],// 当前第一集分镜          │
│    "adjustment_history": [               // 调整历史链             │
│      {"turn": 1, "instruction": "...", "summary_of_changes": "..."}│
│    ]                                                              │
│  }                                                                │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 增量调整 Prompt 构造

```python
INCREMENTAL_ADJUSTMENT_PROMPT = """
你是一个短剧编剧助手。以下是一个短剧项目的当前状态，请根据用户的调整要求修改相应内容。

## 项目当前状态
{context_snapshot}

## 调整历史
{adjustment_history}

## 用户本次调整要求
{user_instruction}

## 输出要求
- 只输出被修改的部分，未修改的部分保持不变
- 如果修改影响其他子项的一致性（如修改人物特征影响了分镜中的角色行为），需同时输出受影响的子项
- 以 JSON 格式输出修改后的完整内容（包含修改和未修改的部分）
"""
```

### 5.4 调整粒度策略

| 调整类型 | 影响范围 | 处理方式 |
|----------|----------|----------|
| 仅修改某个人物特征 | 人物特征 + 可能影响分镜 | 传递当前状态 → 模型判断是否需要联动修改 |
| 仅修改某个场景描写 | 场景描写 + 可能影响分镜 | 同上 |
| 修改故事走向/人物关系 | 所有大纲 + 分镜 | 传递当前状态 → 全量重新生成受影响子项 |
| 修改风格基调 | 全部子项 | 传递当前状态 → 全量重新生成 |

### 5.5 关键实现细节

1. **首次生成时同步构建 ContextSnapshot**: 在 Step 1 全局设定生成后，将小说摘要 + 全局设定作为快照基础；Step 2 各子项完成后，将结果追加到快照
2. **调整历史链**: 每次调整记录 `{turn, instruction, summary_of_changes}`，防止模型在多轮调整中遗忘早期约束
3. **快照持久化**: ContextSnapshot 存储在 `analysis_version.adjustment_context` 字段中，随版本链传递
4. **小说摘要质量**: 首次生成时用模型生成高质量摘要（包含核心情节、人物弧线、关键冲突），这是增量调整质量的关键
5. **兜底机制**: 如果增量调整结果质量下降（用户连续调整 3 次仍不满意），建议用户"基于当前状态重新生成"——此时仍使用 ContextSnapshot 而非原始小说

### 5.6 Token 成本对比

| 场景 | 全量方案 | 增量方案 | 节省 |
|------|----------|----------|------|
| 10万字小说首次生成 | ~130K input tokens | ~130K input tokens | 0% |
| 首次调整 | ~130K input tokens | ~8K input tokens | **94%** |
| 第2次调整 | ~130K input tokens | ~10K input tokens | **92%** |
| 第3次调整 | ~130K input tokens | ~12K input tokens | **91%** |

> 增量方案中，每次调整的 input token 主要来自 ContextSnapshot（~5K-8K）+ 调整历史（递增 ~1-2K/轮）+ 用户指令（~0.5K）

---

## 六、任务可靠性保障

### 6.1 任务生命周期状态机

```
                    ┌──────────┐
          ┌────────▶│ pending  │
          │         └────┬─────┘
          │              │ Worker 领取
          │              ▼
          │         ┌──────────┐
          │         │ running  │─────── 超时 ──────▶ timeout
          │         └────┬─────┘
          │              │
          │    ┌─────────┼──────────┐
          │    ▼         ▼          ▼
          │  success   failed    cancelled
          │              │
          │              │ 重试次数 < max_retries
          │              ▼
          │         ┌──────────┐
          └─────────│ pending  │  (重置为 pending, retry_count++)
                    └──────────┘
```

### 6.2 可靠性机制

| 需求 | 实现方案 |
|------|----------|
| **任务不丢失** | 任务入队时同步写入 `task_record` 表（PG 持久化），Redis 队列仅做分发通道 |
| **失败可重试** | Celery `retry` 机制 + `task_record` 记录重试次数，支持指数退避 |
| **重启可恢复** | Beat 定时扫描 `task_record` 中 `status=running` 且 `timeout_at < now()` 的记录，重新投递 |
| **不重复执行** | 任务领取时通过 PG `SELECT ... FOR UPDATE` 行锁 + `status` 状态检查，确保同一任务只有一个 Worker 执行 |
| **卡住检测恢复** | Beat 每 60s 扫描超时任务，标记为 `timeout` 并重新投递；每个任务类型有独立超时阈值 |

### 6.3 伪代码实现

```python
# 任务入队（双重保障：PG 记录 + Redis 队列）
async def submit_task(project_id, task_type, input_params, timeout_seconds):
    task_id = generate_snowflake_id()

    # 1. PG 持久化
    task_record = TaskRecord(
        id=task_id,
        project_id=project_id,
        task_type=task_type,
        status="pending",
        input_params=input_params,
        max_retries=3,
        timeout_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
    )
    db.add(task_record)
    await db.commit()

    # 2. 投递 Celery 队列
    celery_result = execute_task.apply_async(
        kwargs={"task_id": str(task_id)},
        task_id=str(task_id),
    )

    # 3. 回写 celery_task_id
    task_record.celery_task_id = celery_result.id
    await db.commit()

    return task_id


# Worker 领取任务（防重复执行）
@celery_app.task(bind=True)
def execute_task(self, task_id):
    with SessionLocal() as db:
        # 行锁 + 状态检查
        task = db.query(TaskRecord).filter(
            TaskRecord.id == task_id
        ).with_for_update().one()

        if task.status != "pending":
            return  # 已被其他 Worker 领取

        task.status = "running"
        task.worker_id = self.request.hostname
        task.started_at = datetime.utcnow()
        db.commit()

    try:
        result = dispatch_task(task.task_type, task.input_params)

        with SessionLocal() as db:
            task = db.query(TaskRecord).get(task_id)
            task.status = "success"
            task.output_result = result
            task.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        with SessionLocal() as db:
            task = db.query(TaskRecord).get(task_id)
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = "pending"
                task.next_retry_at = datetime.utcnow() + timedelta(
                    seconds=2 ** task.retry_count * 30  # 指数退避: 30s, 60s, 120s
                )
            else:
                task.status = "failed"
                task.error_message = str(e)
            db.commit()


# Beat 定时检测（卡住任务恢复 + 待重试任务投递）
@celery_app.task
def health_check():
    now = datetime.utcnow()

    with SessionLocal() as db:
        # 1. 检测超时任务
        timed_out = db.query(TaskRecord).filter(
            TaskRecord.status == "running",
            TaskRecord.timeout_at < now,
        ).all()

        for task in timed_out:
            task.status = "timeout"
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = "pending"
                task.timeout_at = now + timedelta(...)
                execute_task.apply_async(kwargs={"task_id": str(task.id)})
            db.commit()

        # 2. 投递待重试任务
        pending_retries = db.query(TaskRecord).filter(
            TaskRecord.status == "pending",
            TaskRecord.next_retry_at < now,
            TaskRecord.retry_count > 0,
        ).all()

        for task in pending_retries:
            execute_task.apply_async(kwargs={"task_id": str(task.id)})
            db.commit()

        # 3. 检测服务重启后遗留的 running 任务
        stale_running = db.query(TaskRecord).filter(
            TaskRecord.status == "running",
            TaskRecord.started_at < now - timedelta(minutes=10),
            ~TaskRecord.worker_id.in_(get_active_workers()),
        ).all()

        for task in stale_running:
            task.status = "pending"
            task.worker_id = None
            execute_task.apply_async(kwargs={"task_id": str(task.id)})
            db.commit()
```

---

## 七、实时通信方案

### 7.1 为什么选择 WebSocket 而非 SSE

SSE 和 WebSocket 在页面刷新时**都会断开连接**，这是浏览器行为，与协议无关。刷新后事件不丢失靠的是服务端消息缓冲机制，而不是协议本身。

选择统一 WebSocket 的真正理由：

1. **业务需要双向通信**: 用户在线调整剧情（输入提示词 → 模型流式输出 → 实时展示）是双向交互，SSE 只支持单向推送，还需要额外开 WebSocket 做交互 → 每个用户维护两条长连接，复杂且浪费
2. **单一协议更简单**: 用一种协议 + 一套缓冲机制，比 SSE + WebSocket 双协议两套机制维护成本低
3. **恢复流程一致**: 刷新后统一走 REST API 查当前状态 → WebSocket 重连 → 缓冲区补发

### 7.2 方案：统一 WebSocket + Redis 消息缓冲 + REST 兜底

```
┌─────────┐     WebSocket      ┌──────────────┐     Pub/Sub     ┌─────────┐
│  前端    │◄══════════════════►│  FastAPI      │◄══════════════►│  Redis  │
│  客户端  │                    │  WS Handler   │                 │  缓冲区  │
└─────────┘                    └──────────────┘                 └─────────┘
     │                              │                                │
     │  1. 连接时上报 last_event_id  │                                │
     │─────────────────────────────►│                                │
     │                              │  2. 查 Redis 缓冲区补发缺失事件   │
     │                              │───────────────────────────────►│
     │                              │◄──────────────────────────────│
     │  3. 补发缺失事件              │                                │
     │◄─────────────────────────────│                                │
     │                              │                                │
     │  4. 后续实时推送              │  5. Worker 写入 Redis + 发布    │
     │◄════════════════════════════│◄═══════════════════════════════│
```

### 7.3 连接管理

| 机制 | 实现 |
|------|------|
| **连接上限** | 每用户最多 3 个并发 WebSocket 连接，超出时关闭最早的一个 |
| **心跳检测** | 客户端每 30s 发 ping，服务端 60s 无心跳则主动断开 |
| **断线重连** | 客户端自动重连，连接时携带 `last_event_id`，服务端从 Redis 缓冲区补发 |
| **消息缓冲** | Redis List 存储每个用户最近 10 分钟的事件，自动过期清理 |
| **连接注册** | Redis Hash 记录 `{user_id: [conn_id, conn_id, ...]}`，用于定向推送 |

### 7.4 消息格式

```json
{
  "event_id": "evt_snowflake_id",
  "event_type": "task_progress|task_completed|task_failed|phase_changed|version_ready|model_stream",
  "project_id": "proj_xxx",
  "timestamp": "2026-05-18T10:30:00Z",
  "data": { ... }
}
```

### 7.5 消息缓冲与回放

```python
class WSMessageBuffer:
    """基于 Redis 的 WebSocket 消息缓冲区"""

    BUFFER_TTL = 600  # 10 分钟
    MAX_EVENTS = 500  # 每用户最多缓存 500 条

    async def publish(self, user_id: str, event: dict):
        """发布事件：写入缓冲区 + Pub/Sub 通知"""
        key = f"ws:buffer:{user_id}"
        # 1. 写入 List（左进右出）
        await self.redis.lpush(key, json.dumps(event))
        await self.redis.ltrim(key, 0, self.MAX_EVENTS - 1)
        await self.redis.expire(key, self.BUFFER_TTL)
        # 2. Pub/Sub 通知在线连接
        await self.redis.publish(f"ws:user:{user_id}", json.dumps(event))

    async def replay_since(self, user_id: str, last_event_id: str) -> list:
        """回放 last_event_id 之后的所有事件"""
        key = f"ws:buffer:{user_id}"
        events = await self.redis.lrange(key, 0, -1)
        result = []
        for raw in reversed(events):
            event = json.loads(raw)
            if event["event_id"] == last_event_id:
                break
            result.append(event)
        return list(reversed(result))
```

### 7.6 刷新恢复完整流程

```
页面刷新
    │
    ▼
前端页面加载
    │
    ├──▶ 1. REST GET /api/v1/project/{id}/status
    │       从 PG 查询最新状态（任务进度、当前阶段、最新版本）
    │       用 PG 数据渲染页面（保证刷新后页面不空白）
    │
    └──▶ 2. WebSocket connect
            发送 {type: "reconnect", last_event_id: "xxx"}
            │
            ├─ 有 last_event_id → Redis 缓冲区补发缺失事件 → 覆盖页面状态
            └─ 无 last_event_id → 直接开始接收新事件
```

关键点：**REST 兜底保证页面始终有数据，WebSocket 缓冲补发保证不遗漏实时变更。**

### 7.7 WebSocket vs SSE 对比

| 维度 | SSE | WebSocket (最终方案) |
|------|-----|---------------------|
| 刷新断连 | 会断 | 也会断（两者一样） |
| 刷新恢复 | 需自建缓冲，且 SSE 协议层面无标准回放机制 | 需自建缓冲，但 WS 消息协议自定义更灵活 |
| 双向通信 | 不支持，需要另开 WebSocket | 原生支持（调整交互 + 流式输出 + 进度推送，一连接覆盖全部） |
| 连接数量 | 如果用 SSE+WS 双协议 = 2 条/用户 | 单协议 = 1 条/用户 |
| 结论 | 多协议叠加，复杂度高 | 单一协议，统一管理 |

---

## 八、日志方案

### 8.1 日志分级

| 日志类型 | 存储位置 | 用途 | 保留策略 |
|----------|----------|------|----------|
| 应用日志 | 文件 + 云存储 | 通用运行日志 | 本地7天，云存储30天 |
| 任务执行日志 | 文件 + 云存储 | 每步操作、发送数据、返回数据、报错/重试 | 本地7天，云存储90天 |
| 模型调用日志 | **PG 分区表** + 文件 + 云存储 | 详细调用记录，支持查询统计 | PG 保留3个月，归档到云存储 |
| 操作记录 | PG `operation_record` 表 | 关键业务操作，前端展示 | 永久 |

### 8.2 模型调用日志（model_call_log）

**写入性能优化：**

```
Worker 调用模型
     │
     ▼
模型返回结果
     │
     ├──▶ 1. 立即写入 Redis List（缓冲区）
     │       key: log:buffer:model_call
     │       每条记录包含完整调用信息
     │
     ├──▶ 2. 同时写入文件（实时，确保不丢失）
     │
     └──▶ 3. Beat 定时任务每 5 秒批量刷入 PG
              从 Redis List 批量取出 → executemany → 清空已刷入的记录
              批量大小: 100 条/次
              失败时保留在 Redis，下次重试
```

**分区表策略：**

```sql
-- 按月自动分区（通过 pg_partman 扩展或 Alembic 迁移脚本）
-- 查询当月数据只扫描当月分区，历史查询走对应月份分区
-- 超过 3 个月的分区通过 pg_partman 自动 detach 并归档到云存储
```

**关键字段设计理由：**

| 字段 | 理由 |
|------|------|
| request_id | 调用端生成的唯一 ID，用于全链路追踪 |
| api_key_masked | 脱敏存储（sk-***abc），用于排查哪个 Key 被限流 |
| request_body | 存完整请求体（JSONB），排错和回放必需 |
| response_body | 存响应体摘要（大响应截断），排错用 |
| latency_ms | 监控模型 API 响应时间趋势 |
| is_retry + retry_count | 区分首次调用和重试，统计重试率 |

### 8.3 任务记录表（task_record）分区与归档

**问题**: task_record 表会持续增长，每个项目可能产生数百条任务记录。

**方案: 按月分区 + 冷数据归档**

```
┌─────────────────────────────────────────────────┐
│ task_record (分区主表)                            │
│                                                   │
│ ┌──────────────────┐  ┌──────────────────┐       │
│ │ task_record_     │  │ task_record_     │  ...  │
│ │ 2026_05          │  │ 2026_06          │       │
│ │ (热数据, 在线查询) │  │ (热数据)         │       │
│ └──────────────────┘  └──────────────────┘       │
│                                                   │
│ ┌──────────────────┐                              │
│ │ task_record_     │  超过3个月 → DETACH 分区     │
│ │ 2026_02          │───────────────────────▶      │
│ │ (冷数据)         │         pg_dump 归档到云存储  │
│ └──────────────────┘         然后 DROP 分区       │
└─────────────────────────────────────────────────┘
```

**归档流程:**

1. Beat 每月1号执行归档任务
2. 检查超过 3 个月的分区
3. `pg_dump -t task_record_YYYY_MM` 导出到云存储
4. `ALTER TABLE task_record DETACH PARTITION task_record_YYYY_MM`
5. `DROP TABLE task_record_YYYY_MM`
6. 归档元信息记录到 `task_record_archive_meta` 表

### 8.4 项目日志方案

**结论: 项目日志不存入数据库表**

理由：
- 日志量极大（每步操作、发送数据、模型返回均记录），写入 PG 影响业务库性能
- 日志的主要需求是"按项目下载"，文件系统直接满足
- 如果需要前端展示关键操作，已有 `operation_record` 表覆盖

**实现:**

```
存储路径: /logs/{project_id}/
  ├── app_{date}.log          # 应用日志
  ├── task_{date}.log         # 任务执行日志（每步详细记录）
  └── model_call_{date}.log   # 模型调用日志

日志格式 (JSON Lines):
{
  "ts": "2026-05-18T10:30:00.123Z",
  "project_id": "proj_xxx",
  "level": "INFO",
  "module": "text_analysis",
  "task_id": "task_xxx",
  "action": "model_call",
  "request_data": { ... },       # 发送给模型的数据摘要
  "response_data": { ... },      # 模型返回数据摘要
  "is_retry": false,
  "retry_count": 0,
  "error": null,
  "latency_ms": 3500
}

归档: 超过 7 天的日志文件自动上传到云存储 {bucket}/logs/{project_id}/
```

### 8.5 日志详细度要求

每一步操作至少记录以下信息：

| 场景 | 记录内容 |
|------|----------|
| 任务开始 | task_id, task_type, input_params, worker_id |
| 模型调用前 | request_id, model_provider, model_name, endpoint, request_body 摘要 |
| 模型调用后 | response_status, input_tokens, output_tokens, total_tokens, latency_ms |
| 模型调用失败 | error_message, is_retry, retry_count, next_retry_at |
| 任务完成 | task_id, output_result 摘要, total_latency_ms |
| 用户操作 | user_id, action, target_type, target_id, detail |

---

## 九、模型调用抽象层

### 9.1 统一接口

```python
class ModelProvider(ABC):
    """模型调用抽象基类"""

    @abstractmethod
    async def generate(self, prompt: str, config: ModelConfig) -> ModelResult:
        """生成内容"""

    @abstractmethod
    async def generate_stream(self, prompt: str, config: ModelConfig) -> AsyncIterator[str]:
        """流式生成"""

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """计算 token 数"""

class TextModelProvider(ModelProvider): ...
class ImageModelProvider(ModelProvider): ...
class VideoModelProvider(ModelProvider): ...

class ModelRouter:
    """模型路由器：根据配置选择供应商，支持故障转移"""

    def __init__(self, providers: dict[str, ModelProvider]):
        self.providers = providers
        self.health_status: dict[str, bool] = {}

    async def generate(self, prompt, config):
        primary = config.provider
        if self.health_status.get(primary, True):
            try:
                return await self.providers[primary].generate(prompt, config)
            except ModelAPIError:
                self.health_status[primary] = False

        # 故障转移
        for fallback in config.fallback_providers:
            if self.health_status.get(fallback, True):
                try:
                    return await self.providers[fallback].generate(prompt, config)
                except ModelAPIError:
                    continue

        raise AllProvidersFailedError()
```

### 9.2 调用日志集成

每次模型调用自动记录到 `model_call_log`，无需业务代码手动埋点：

```python
class LoggingModelProvider(ModelProvider):
    """带日志记录的模型调用装饰器"""

    def __init__(self, provider: ModelProvider, log_writer: ModelCallLogWriter):
        self._provider = provider
        self._log_writer = log_writer

    async def generate(self, prompt, config):
        request_id = generate_request_id()
        start = time.monotonic()
        try:
            result = await self._provider.generate(prompt, config)
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log_writer.write(
                request_id=request_id,
                model_provider=config.provider,
                model_name=config.model_name,
                endpoint=config.endpoint,
                api_key_masked=mask_api_key(config.api_key),
                request_body={"prompt_preview": prompt[:500], "config": config.dict()},
                response_status=200,
                response_body={"result_preview": str(result)[:500]},
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                total_tokens=result.usage.total_tokens,
                latency_ms=latency_ms,
            )
            return result
        except Exception as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            await self._log_writer.write(
                request_id=request_id,
                ...,
                response_status=getattr(e, "status_code", 0),
                error_message=str(e),
                latency_ms=latency_ms,
                is_retry=config.is_retry,
                retry_count=config.retry_count,
            )
            raise
```

---

## 十、并发处理与资源管理

### 10.1 任务优先级队列

```python
# Celery 队列分离
CELERY_TASK_ROUTES = {
    "app.tasks.text_analysis.*": {"queue": "text"},
    "app.tasks.image_generation.*": {"queue": "image"},
    "app.tasks.video_generation.*": {"queue": "video"},
    "app.tasks.health_check": {"queue": "beat"},
}

# 每个队列独立 Worker，避免资源争抢
# text:  4 Worker (文本任务 CPU 密集)
# image: 2 Worker (图片生成并发受 API 限制)
# video: 1 Worker (视频生成最耗时，避免并发过多)
```

### 10.2 限流策略

```python
# 基于 Redis 令牌桶的 API 限流
class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def acquire(self, key: str, max_tokens: int, refill_rate: float):
        """令牌桶限流"""
        now = time.time()
        pipe = self.redis.pipeline()
        pipe.hgetall(key)
        data = await pipe.execute()

        # 计算当前可用令牌...
        if available_tokens > 0:
            await self.redis.hincrby(key, "tokens", -1)
            return True
        return False

# 限流配置
RATE_LIMITS = {
    "text_model_per_user": {"max": 10, "refill": 1},      # 每用户每分钟10次
    "image_model_per_user": {"max": 5, "refill": 0.5},    # 每用户每分钟5次
    "video_model_per_user": {"max": 2, "refill": 0.2},    # 每用户每分钟2次
    "text_model_global": {"max": 50, "refill": 5},         # 全局每分钟50次
}
```

---

## 十一、总结与建议

### 11.1 架构决策汇总

| 决策 | 选择 | 理由 |
|------|------|------|
| 剧情分析子项是否并发 | **分层依赖并发** | 串行1步(全局设定) + 并发1步(4子项) + 串行1步(第一集分镜) |
| 调整时是否重传小说 | **否，使用增量上下文** | 节省 90%+ token，速度快 5-10 倍 |
| 任务持久化 | **PG + Redis 双写** | PG 保可靠，Redis 保性能 |
| 实时通信 | **统一 WebSocket** | SSE 刷新丢会话，WS + Redis 缓冲可回放 |
| 模型调用 | **抽象层 + 故障转移** | 解耦供应商依赖，提高可用性 |
| 资产表设计 | **按人物/场景/道具分表，图片字段收归主表，每资产一张图** | 无独立图片子表，image_url/image_prompt/gen_status 直接存主表，查询无需 JOIN |
| 项目日志存储 | **仅文件 + 云存储，不入库** | 日志量大影响性能，operation_record 覆盖前端需求 |
| 模型调用日志 | **PG 分区表 + Redis 缓冲批量写入** | 高频写入，分区保查询性能，缓冲保写入性能 |
| 任务记录表 | **PG 按月分区 + 冷归档** | 控制表大小，热数据在线，冷数据归档云存储 |
| 图片生成 | **支持用户修改提示词重新生成** | 修改 description/prompt 后触发重新生成，直接覆盖 image_url |

### 11.2 数据流

#### 11.2.1 实体关系总览

```
Project (项目)
  ├── 1:1 AnalysisResult (分析结果)
  │       └── 1:N AnalysisVersion (分析版本，每次生成/调整一条)
  │               ├── global_setting (全局设定 JSON)
  │               ├── character_profiles (人物特征 JSON)
  │               ├── scene_descriptions (场景描写 JSON)
  │               ├── prop_descriptions (道具描写 JSON)
  │               ├── episode_outlines (每集大纲 JSON)
  │               ├── first_ep_storyboard (第一集分镜 JSON)
  │               └── adjustment_context (增量调整上下文 JSON)
  │
  ├── 1:N ProjectCharacter (项目人物/角色)
  ├── 1:N ProjectLocation  (项目场景)
  ├── 1:N ProjectProp      (项目道具)
  │
  ├── 1:N Episode (剧集)
  │       └── 1:N Storyboard (分镜)
  │               └── 1:N VideoClip (视频片段)
  │
  └── 1:N OperationRecord (操作记录)

User (用户)
  ├── 1:N GlobalCharacter (全局人物)
  ├── 1:N GlobalLocation  (全局场景)
  ├── 1:N GlobalProp      (全局道具)
  ├── 1:N GlobalVoice     (全局音色)
  └── 1:N GlobalAssetFolder (资产文件夹)
```

#### 11.2.2 阶段一：故事分析（`draft → analyzingStory → storyReady → projectCreated`）

| 步骤 | 写入操作 | 目标表 |
|------|----------|--------|
| 点击「开始创作」 | INSERT project (status=draft, novel_text) + INSERT analysis_result (status=pending) | `project` + `analysis_result` |
| 自动触发分析 | UPDATE project (status=analyzingStory) + INSERT analysis_version (version_number=1) | `project` + `analysis_version` |
| Celery Layer 0 预处理 | UPDATE project (novel_meta) | `project` |
| Celery Layer 1 详尽提取 | UPDATE analysis_version (token_usage) | `analysis_version` |
| Celery Layer 2 格式化 | 各子结果写入内存 | — |
| Celery 汇总写入 | UPDATE analysis_version (global_setting, character_profiles, scene_descriptions, prop_descriptions, episode_outlines, first_ep_storyboard, adjustment_context) + UPDATE project (status=storyReady) + UPDATE analysis_result (status=completed) | `analysis_version` + `project` + `analysis_result` |
| WS 推送 analysis_completed | — | — |
| 用户确认 | UPDATE project (title, config, status=projectCreated) + UPDATE analysis_version (is_confirmed=true) | `project` + `analysis_version` |
| 用户调整 | UPDATE project (status=analyzingStory) + INSERT analysis_version (version_number=N+1, parent_version_id=上一版) | `project` + `analysis_version` |

#### 11.2.3 阶段二：资产生成（`projectCreated → assetsReady`）

| 数据来源 | 写入目标 | 说明 |
|----------|----------|------|
| `analysis_version.character_profiles` → 解析每个角色 | INSERT `project_character` (name, description, image_prompt, gen_status=pending) | 从 JSON 文本中提取角色名和视觉提示词 |
| `analysis_version.scene_descriptions` → 解析每个场景 | INSERT `project_location` (name, description, image_prompt, gen_status=pending) | 从 JSON 文本中提取场景名和视觉提示词 |
| `analysis_version.prop_descriptions` → 解析每个道具 | INSERT `project_prop` (name, description, image_prompt, gen_status=pending) | 从 JSON 文本中提取道具名和视觉提示词 |
| 确认后 → 图片生成 | UPDATE `project_character/location/prop` (image_url, gen_status=completed) | 调用图片模型生成 |
| 全部完成 | UPDATE project (status=assetsReady) | — |

#### 11.2.4 阶段三：剧集制作（`assetsReady → producing → completed`）

> **未实现**

| 步骤 | 写入操作 | 目标表 |
|------|----------|--------|
| 从 `episode_outlines` 创建剧集 | INSERT `episode` (episode_number, outline, status=pending) | `episode` |
| 生成分镜 | INSERT `storyboard` (shot_number, description, reference_image) | `storyboard` |
| 生成视频 | INSERT `video_clip` (status=generating) → UPDATE (video_url, status=completed) | `video_clip` |
| 全部完成 | UPDATE project (status=completed) | `project` |

#### 11.2.5 关键设计：analysis_version 与独立资产表的关系

**`analysis_version`** 存储的是 AI 生成的**原始文本结果**（JSON），服务于故事分析阶段的展示和调整。

**`project_character/location/prop`** 存储的是**独立资产实体**，服务于图片生成和跨集复用，有独立的 `image_url`、`gen_status`、`voice_id` 等字段。

两者之间的桥梁是**阶段二的拆分写入逻辑**：从 `analysis_version` 的 JSON 文本中解析出角色/场景/道具的结构化数据，创建对应的资产记录。示意图：

```
analysis_version.character_profiles (JSON 文本)
       │
       ▼  解析拆分
  ┌────┴────┬─────────┐
  ▼         ▼         ▼
张三      李四      王五
  │         │         │
  ▼         ▼         ▼
INSERT   INSERT    INSERT         ← 阶段二触发
project_character × N 条
  │
  ▼  图片生成
UPDATE image_url, gen_status      ← 阶段二后续
```
