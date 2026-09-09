# 日志系统技术设计

> 版本: v1.0 | 日期: 2026-05-19 | 作者: 产品经理
> 关联文档: [系统架构设计 v1.1](drama-production-architecture.md) | [故事分析详细设计](story-analysis-detail-design.md)

---

## 一、设计目标

| 目标 | 说明 |
|------|------|
| **可追溯** | 每一步操作、每一次模型调用都有据可查，支持问题定位和复现 |
| **按项目隔离** | 项目日志独立存储，支持按项目下载 |
| **高性能写入** | 模型调用日志高频写入，不影响业务库性能 |
| **易读友好** | 文件日志人类可读，符合 Python 日志规范 |
| **可查询** | 模型调用日志入库，支持按用户/项目/模型/时间维度查询和统计 |

---

## 二、日志分类体系

```
日志体系
├── 1. 公共日志（文件）
│   ├── app.log          # 全量应用日志（INFO 及以上）
│   └── error.log        # 仅错误日志（ERROR 及以上）
│
├── 2. 项目日志（文件，按项目隔离，不按日期拆分）
│   └── logs/projects/{project_id}/
│       ├── project.log       # 项目运行日志
│       ├── task.log          # 任务执行日志（每步详细记录）
│       └── model_call.log    # 模型调用日志（人类可读，详细JSON在message字段）
│
├── 3. 模型调用日志（数据库分区表 + 文件）
│   ├── PostgreSQL model_call_log 表（查询统计）
│   └── model_call.log 文件（完整请求/响应，供下载）
│
└── 4. 操作记录（数据库表）
    └── operation_record 表（关键业务操作，永久保留）
```

**存储策略**：

| 日志类型 | 文件 | 数据库 | 保留策略             |
|----------|------|--------|------------------|
| 公共日志 | app.log / error.log | - | 本地 90 天          |
| 项目日志 | 按项目目录 | - | 本地 90 天 |
| 模型调用日志 | model_call.log | model_call_log 分区表 | PG 1 年，文件 90 天   |
| 操作记录 | - | operation_record 表 | 永久               |

---

## 三、公共日志设计

### 3.1 文件说明

| 文件 | 级别 | 内容 |
|------|------|------|
| `logs/app_{YYYY-MM-DD}.log` | INFO 及以上 | 全量应用日志，包含启动、请求、业务逻辑、任务调度等 |
| `logs/error_{YYYY-MM-DD}.log` | ERROR 及以上 | 仅错误和严重错误，便于快速定位异常 |

### 3.2 日志格式

```
2026-05-19 10:30:00.123 | INFO     | core.config:load_config:45 - 应用配置加载完成
2026-05-19 10:30:01.456 | ERROR    | core.model_provider:generate:62 - 模型调用失败 model=deepseek-chat latency=3500ms error=ConnectionTimeout
```

**格式规范**：

```
{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}.{name}:{function}:{line} - {message}
```

- 时间精确到毫秒
- 日志级别固定 8 字符宽度左对齐
- 模块路径使用点分隔，便于定位
- 消息体使用结构化键值对，便于 grep

### 3.3 日志轮转

| 配置项 | 值         | 说明          |
|--------|-----------|-------------|
| rotation | `00:00`   | 每天零点轮转      |
| retention | `90 days` | 公共日志保留 90 天 |
| compression | `zip`     | 轮转后自动压缩     |

---

## 四、项目日志设计

### 4.1 目录结构

```
backend/logs/
├── app_2026-05-19.log                      # 公共应用日志
├── error_2026-05-19.log                    # 公共错误日志
└── projects/
    ├── proj_1234567890/
    │   ├── project.log                      # 项目运行日志
    │   ├── task.log                         # 任务执行日志
    │   └── model_call.log                   # 模型调用日志
    └── proj_9876543210/
        ├── project.log
        ├── task.log
        └── model_call.log
```

### 4.2 文件说明

| 文件 | 用途 | 格式 |
|------|------|------|
| `project.log` | 项目级别运行日志：状态变更、用户操作、业务流转 | 人类可读 |
| `task.log` | 任务执行日志：每步操作的详细记录 | 人类可读 |
| `model_call.log` | 模型调用完整记录：请求体、响应体、耗时、token | 人类可读，详细JSON信息放在message字段 |

### 4.3 项目日志格式

**project.log（人类可读）**：

```
2026-05-19 10:30:00.123 | INFO     | project:proj_123 | 状态变更 draft → analyzingStory
2026-05-19 10:30:05.456 | INFO     | project:proj_123 | 用户 user_456 确认项目设置 title="我的短剧" ratio=9:16 style=realistic
2026-05-19 10:35:00.789 | ERROR    | project:proj_123 | 分析任务失败 task_id=task_789 error="模型返回格式错误"
```

**task.log（人类可读）**：

```
2026-05-19 10:30:00.123 | INFO     | task:task_789 | [comprehensive_extraction] 任务开始 project=proj_123
2026-05-19 10:30:00.456 | INFO     | task:task_789 | [comprehensive_extraction] 发送模型请求 model=deepseek-chat prompt_len=12500 input_tokens≈8000
2026-05-19 10:32:30.789 | INFO     | task:task_789 | [comprehensive_extraction] 模型返回成功 latency=150456ms output_tokens≈3200
2026-05-19 10:32:31.000 | INFO     | task:task_789 | [comprehensive_extraction] 任务完成 总耗时=150877ms
```

**model_call.log（人类可读，详细JSON在message字段）**：

```
2026-05-19 10:30:00.456 | INFO     | core.model_provider:generate:58 - [project:proj_123] 模型调用开始 request_id=req_snowflake_id model=deepseek-chat endpoint=https://api.deepseek.com/v1/chat/completions prompt_len=12500 detail={"request_id":"req_snowflake_id","model_provider":"openai_compatible","model_name":"deepseek-chat","endpoint":"https://api.deepseek.com/v1/chat/completions","prompt_preview":"你是一个专业的短剧编剧...","prompt_len":12500,"messages_count":2,"temperature":0.7,"max_tokens":8192}
2026-05-19 10:32:30.789 | INFO     | core.model_provider:generate:58 - [project:proj_123] 模型调用完成 request_id=req_snowflake_id status=200 input_tokens=8123 output_tokens=3245 total_tokens=11368 latency=150333ms detail={"request_id":"req_snowflake_id","action":"model_call_end","response_status":200,"input_tokens":8123,"output_tokens":3245,"total_tokens":11368,"latency_ms":150333,"usage_details":{"prompt_cache_hit_tokens":5000},"response_preview":"{\"novel_summary\":\"故事讲述了...\"}","choices_count":1,"finish_reason":"stop"}
```

### 4.4 按项目下载

提供 API 接口，将指定项目的全部日志打包下载：

```
GET /api/v1/projects/{id}/logs

响应: ZIP 文件
  ├── project.log
  ├── task.log
  └── model_call.log
```

### 4.5 日志轮转与清理

| 配置项 | 值                                           |
|--------|---------------------------------------------|
| retention | `90 days`（本地保留 90 天）                        |
| compression | `zip`                                       |

---

## 五、模型调用日志设计

### 5.1 数据表设计

#### 5.1.1 通用 Usage 字段分析

不同模型供应商返回的 usage 结构：

| 供应商 | 通用字段 | 供应商特有字段 |
|--------|----------|----------------|
| OpenAI | input_tokens, output_tokens, total_tokens | prompt_tokens_details.cached_tokens, completion_tokens_details.reasoning_tokens |
| Anthropic | input_tokens, output_tokens | cache_creation_input_tokens, cache_read_input_tokens |
| DeepSeek | input_tokens, output_tokens, total_tokens | prompt_cache_hit_tokens, prompt_cache_miss_tokens |
| 智谱 (Zhipu) | input_tokens, output_tokens, total_tokens | - |
| 火山方舟 (Volcengine Ark) | prompt_tokens, completion_tokens, total_tokens | - |

> **说明**：火山方舟使用 OpenAI 兼容接口（base_url: `https://ark.cn-beijing.volces.com/api/v3`），返回的 usage 结构与 OpenAI 一致（prompt_tokens/completion_tokens/total_tokens）。火山方舟响应中包含 `id` 字段（如 `"id": "0217426318107460cfa43dc3f3683b1de1c09624ff49085a456ac"`），作为模型厂商自身的请求 ID 需完整记录到 `provider_request_id` 字段。参考文档：https://www.volcengine.com/docs/82379/1494384

**结论**：`input_tokens`/`prompt_tokens`、`output_tokens`/`completion_tokens`、`total_tokens` 是所有供应商的通用字段，统一映射为 `input_tokens`、`output_tokens`、`total_tokens` 独立列存储，便于索引和聚合查询。供应商特有字段存入 `usage_details` JSONB。

#### 5.1.2 表结构

```sql
-- ============================================================
-- 模型调用日志（按天分区）
-- ============================================================
CREATE TABLE model_call_log (
    id                  VARCHAR(32) PRIMARY KEY,

    -- 调用上下文
    user_id             VARCHAR(32) NOT NULL,                 -- 调用用户
    project_id          VARCHAR(32),                           -- 关联项目（系统级调用可为空）
    task_id             VARCHAR(32),                           -- 关联任务

    -- 请求标识
    request_id          VARCHAR(128) NOT NULL,                -- 调用端生成的唯一请求 ID（全链路追踪）
    provider_request_id VARCHAR(256),                          -- 模型厂商返回的请求 ID（如火山方舟的 id 字段）

    -- 模型信息
    model_provider      VARCHAR(64) NOT NULL,                 -- 供应商: openai/anthropic/zhipu/deepseek/volcengine/...
    model_name          VARCHAR(128) NOT NULL,                -- 模型名: gpt-4o/deepseek-chat/...
    endpoint            VARCHAR(512) NOT NULL,                -- API 端点 URL
    api_key_masked      VARCHAR(64),                          -- 脱敏后的 API Key (sk-***abc)

    -- 请求/响应摘要（大内容截断，完整内容见文件日志）
    request_body        JSONB,                                -- 请求体（prompt 截断至 2000 字符）
    response_status     INTEGER,                              -- HTTP 状态码
    response_body       JSONB,                                -- 响应体摘要（截断至 2000 字符）

    -- 通用 Usage 字段（独立列，所有供应商共有）
    input_tokens        INTEGER DEFAULT 0,                   -- 输入 token 数
    output_tokens       INTEGER DEFAULT 0,                   -- 输出 token 数
    total_tokens        INTEGER DEFAULT 0,                   -- 总 token 数
    latency_ms          INTEGER,                              -- 调用耗时（毫秒）

    -- 供应商特有 Usage（JSONB）
    usage_details       JSONB,                                -- 供应商特有字段，如:
                                                         -- OpenAI: {"cached_tokens":80,"reasoning_tokens":10}
                                                         -- Anthropic: {"cache_creation_input_tokens":0,"cache_read_input_tokens":80}
                                                         -- DeepSeek: {"prompt_cache_hit_tokens":5000}
                                                         -- Volcengine: {}（无特有字段）

    -- 重试
    is_retry            BOOLEAN NOT NULL DEFAULT FALSE,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    max_retries         INTEGER NOT NULL DEFAULT 3,
    error_message       TEXT,

    -- 时间
    call_time           TIMESTAMPTZ NOT NULL,                    -- 模型实际调用时间（请求发出的时刻）
    create_time         TIMESTAMPTZ NOT NULL DEFAULT NOW()       -- 记录入库时间（Redis 缓冲后可能有延迟）

) PARTITION BY RANGE (call_time);
```

#### 5.1.3 分区策略

```sql
-- 按天分区，以 call_time 为分区键（Alembic 迁移脚本自动创建未来 7 天分区）
CREATE TABLE model_call_log_2026_05_19 PARTITION OF model_call_log
    FOR VALUES FROM ('2026-05-19') TO ('2026-05-20');

CREATE TABLE model_call_log_2026_05_20 PARTITION OF model_call_log
    FOR VALUES FROM ('2026-05-20') TO ('2026-05-21');

CREATE TABLE model_call_log_2026_05_21 PARTITION OF model_call_log
    FOR VALUES FROM ('2026-05-21') TO ('2026-05-22');
```

**分区维护**：
- 分区键使用 `call_time`（模型实际调用时间），确保查询时按调用时间裁剪分区
- Alembic 迁移中预建未来 7 天分区
- Beat 每天凌晨执行分区创建任务，自动创建未来 7 天的分区
- 超过 1 年的分区：detach → drop

#### 5.1.4 索引设计

```sql
-- 按用户查询（统计用户调用次数/费用）
CREATE INDEX idx_mcl_user ON model_call_log(user_id);

-- 按项目查询（项目维度统计）
CREATE INDEX idx_mcl_project ON model_call_log(project_id) WHERE project_id IS NOT NULL;

-- 按任务查询（任务链路追踪）
CREATE INDEX idx_mcl_task ON model_call_log(task_id) WHERE task_id IS NOT NULL;

-- 按模型查询（统计各模型调用量/延迟）
CREATE INDEX idx_mcl_model ON model_call_log(model_provider, model_name);

-- 按时间范围查询（分区裁剪已优化，此索引辅助分区内过滤）
CREATE INDEX idx_mcl_time ON model_call_log(call_time);

-- 按状态查询（快速找到失败的调用）
CREATE INDEX idx_mcl_error ON model_call_log(error_message) WHERE error_message IS NOT NULL;
```

### 5.2 写入性能优化

模型调用日志是高频写入场景（每次模型调用一条），直接写 PG 会影响业务库性能。

**方案：Redis 缓冲 + 定时批量写入**

```
Worker 调用模型
     │
     ▼
模型返回结果
     │
     ├──▶ 1. 立即写入文件（model_call.log，确保不丢失）
     │
     └──▶ 2. 立即推入 Redis List（异步，非阻塞）
              key: log:buffer:model_call
              value: JSON 完整记录
                    │
                    ▼
              Beat 定时任务（每 5 秒）
                    │
                    ├── 从 Redis List 批量取出（最多 500 条）
                    ├── executemany() 批量写入 PG
                    └── 删除已写入的记录（RPOP）
```

**关键参数**：

| 参数 | 值 | 说明 |
|------|-----|------|
| Redis 缓冲区 key | `log:buffer:model_call` | List 类型 |
| 批量写入间隔 | 5 秒 | Beat 任务频率 |
| 每批最大条数 | 500 条 | 防止单次写入过大 |
| Redis 溢出保护 | List 最大长度 10000 | LTRIM 裁剪（极端情况） |
| 写入失败处理 | 保留在 Redis，下次重试 | 不丢失 |

**性能估算**：

| 场景 | QPS | 批量写入延迟 | PG 压力 |
|------|-----|-------------|---------|
| 10 个并发分析任务 | ~2 条/秒 | 5 秒内入库 | 每 5 秒 10 条，可忽略 |
| 100 个并发分析任务 | ~20 条/秒 | 5 秒内入库 | 每 5 秒 100 条，可忽略 |
| 极端峰值 500 并发 | ~100 条/秒 | 5 秒内入库 | 每 5 秒 500 条，单批 INSERT 可承受 |

### 5.3 ORM 模型

```python
class ModelCallLog(Base):
    """模型调用日志"""
    __tablename__ = "model_call_log"

    id = Column(String(32), primary_key=True, default=generate_id)

    # 调用上下文
    user_id = Column(String(32), nullable=False, comment="调用用户")
    project_id = Column(String(32), comment="关联项目")
    task_id = Column(String(32), comment="关联任务")

    # 请求标识
    request_id = Column(String(128), nullable=False, comment="唯一请求ID")
    provider_request_id = Column(String(256), comment="模型厂商请求ID")

    # 模型信息
    model_provider = Column(String(64), nullable=False, comment="供应商")
    model_name = Column(String(128), nullable=False, comment="模型名")
    endpoint = Column(String(512), nullable=False, comment="API端点")
    api_key_masked = Column(String(64), comment="脱敏API Key")

    # 请求/响应
    request_body = Column(JSON, comment="请求体")
    response_status = Column(Integer, comment="HTTP状态码")
    response_body = Column(JSON, comment="响应体摘要")

    # 通用 Usage
    input_tokens = Column(Integer, default=0, comment="输入token数")
    output_tokens = Column(Integer, default=0, comment="输出token数")
    total_tokens = Column(Integer, default=0, comment="总token数")
    latency_ms = Column(Integer, comment="调用耗时(毫秒)")

    # 供应商特有 Usage
    usage_details = Column(JSON, comment="供应商特有usage字段")

    # 重试
    is_retry = Column(Boolean, nullable=False, default=False)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_message = Column(Text, comment="错误信息")

    # 时间
    call_time = Column(DateTime, nullable=False, comment="模型实际调用时间")
    create_time = Column(DateTime, nullable=False, default=datetime.now, comment="记录入库时间")
```

> **注意**：`ModelCallLog` 不继承 `BaseMixin`。理由：分区表不支持 UPDATE，不需要 `update_time`/`modifier` 等审计字段；日志记录不做逻辑删除，不需要 `is_deleted`。

### 5.4 查询场景

| 场景 | 查询方式 |
|------|----------|
| 用户查看项目日志 | `WHERE project_id = ? AND call_time BETWEEN ? AND ?` |
| 统计用户 token 消耗 | `SELECT user_id, SUM(total_tokens) GROUP BY user_id` |
| 统计模型调用量 | `SELECT model_provider, model_name, COUNT(*) GROUP BY 1, 2` |
| 统计模型平均延迟 | `SELECT model_name, AVG(latency_ms) GROUP BY 1` |
| 查找失败的调用 | `WHERE error_message IS NOT NULL AND call_time > ?` |
| 按请求 ID 追踪 | `WHERE request_id = ?`（全链路追踪） |
| 费用估算 | `SELECT model_name, SUM(input_tokens), SUM(output_tokens) GROUP BY 1` |

---

## 六、日志详细度要求

### 6.1 任务执行各阶段日志

每个 Celery 任务必须按以下阶段记录日志，使用统一的 `[task_type]` 前缀：

| 阶段 | 日志级别 | 必记字段 | 示例 |
|------|----------|----------|------|
| **1. 任务接收** | INFO | task_id, task_type, project_id, input_params 摘要 | `[comprehensive_extraction] 任务开始 project=proj_123 input_params={"novel_len":50000}` |
| **2. 开始处理** | INFO | 当前步骤、输入数据摘要 | `[comprehensive_extraction] 开始详尽提取 novel_len=50000 chapters=12` |
| **3. 模型请求发送** | INFO | request_id, model_name, prompt 长度、预估 token | `[comprehensive_extraction] 发送模型请求 request_id=req_456 model=deepseek-chat prompt_len=12500 est_tokens≈8000` |
| **4. 模型响应收到** | INFO | request_id, response_status, usage, latency | `[comprehensive_extraction] 模型返回成功 request_id=req_456 status=200 input_tokens=8123 output_tokens=3245 latency=150333ms` |
| **5. 响应解析** | INFO | 解析结果摘要 | `[comprehensive_extraction] 解析完成 characters=8 scenes=12 props=5 episodes=10` |
| **6. 模型调用失败** | ERROR | request_id, error_type, error_message, retry_count | `[comprehensive_extraction] 模型调用失败 request_id=req_456 error=ConnectionTimeout retry=1/3` |
| **7. 重试中** | INFO | request_id, retry_count, next_retry_at | `[comprehensive_extraction] 准备重试 request_id=req_456 retry=2/3 next_retry_at=10:35:00` |
| **8. 任务完成** | INFO | task_id, 输出摘要, 总耗时 | `[comprehensive_extraction] 任务完成 task_id=task_789 output={characters=8,scenes=12} duration=150877ms` |
| **9. 任务失败** | ERROR | task_id, error_message, 所有重试历史 | `[comprehensive_extraction] 任务最终失败 task_id=task_789 retries=3 errors=[ConnectionTimeout, JSONDecodeError, ...]` |

### 6.2 模型调用日志字段明细

每次模型调用必须记录以下完整信息：

| 类别 | 字段 | 是否必填 | 说明 |
|------|------|----------|------|
| **调用上下文** | user_id | 是 | 发起调用的用户 |
| | project_id | 否 | 关联项目 |
| | task_id | 否 | 关联任务 |
| | request_id | 是 | 唯一请求 ID（全链路追踪） |
| | provider_request_id | 否 | 模型厂商返回的请求 ID（如火山方舟 id 字段） |
| **模型信息** | model_provider | 是 | 供应商标识 |
| | model_name | 是 | 模型名称 |
| | endpoint | 是 | API 端点 URL |
| | api_key_masked | 是 | 脱敏后的 API Key |
| **请求** | request_body | 是 | 完整请求体（prompt 截断至 2000 字符存入 DB，完整内容写入文件） |
| **响应** | response_status | 是 | HTTP 状态码 |
| | response_body | 是 | 响应体摘要（截断至 2000 字符存入 DB，完整内容写入文件） |
| **Usage（通用）** | input_tokens | 是 | 输入 token 数 |
| | output_tokens | 是 | 输出 token 数 |
| | total_tokens | 是 | 总 token 数 |
| | latency_ms | 是 | 调用耗时（毫秒） |
| **Usage（特有）** | usage_details | 否 | 供应商特有字段（JSONB） |
| **重试** | is_retry | 是 | 是否重试调用 |
| | retry_count | 是 | 当前重试次数 |
| | max_retries | 是 | 最大重试次数 |
| **错误** | error_message | 否 | 失败时的错误信息 |
| **时间** | call_time | 是 | 模型实际调用时间（请求发出时刻） |
| | create_time | 是 | 记录入库时间（Redis 缓冲后可能有延迟） |

### 6.3 用户操作日志

通过 `operation_record` 表记录关键业务操作：

| 操作 | action 值 | detail 内容 |
|------|-----------|-------------|
| 创建项目 | `create_project` | `{novel_len, file_url}` |
| 上传小说 | `upload_novel` | `{file_name, file_size, format, char_count}` |
| 开始分析 | `start_analysis` | `{version_number}` |
| 确认项目设置 | `confirm_project` | `{title, ratio, style}` |
| 调整分析 | `adjust_analysis` | `{adjustment, version_number}` |
| 保存分镜 | `save_storyboard` | `{scene_count}` |
| 进入下一阶段 | `proceed_next` | `{from_phase, to_phase}` |

---

## 七、日志格式规范

### 7.1 文件日志格式（loguru）

**公共日志和项目日志**，使用统一格式：

```
{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {module}.{name}:{function}:{line} - {message}
```

**示例**：

```
2026-05-19 10:30:00.123 | INFO     | core.model_provider:generate:58 - 模型调用完成 model=deepseek-chat latency=150333ms input_tokens=8123 output_tokens=3245 total_tokens=11368
2026-05-19 10:30:01.456 | WARNING  | tasks.story_analysis:comprehensive_extraction:120 - [comprehensive_extraction] 准备重试 request_id=req_456 retry=2/3 next_retry_at=10:35:00
2026-05-19 10:30:02.789 | ERROR    | core.model_provider:generate:82 - [comprehensive_extraction] 模型调用失败 request_id=req_456 error=ConnectionTimeout retry=1/3
```

### 7.2 项目 model_call.log 格式

项目目录下的模型调用日志使用人类可读格式，与 project.log/task.log 一致，详细 JSON 信息放在 message 字段中：

```
2026-05-19 10:30:00.456 | INFO     | core.model_provider:generate:58 - [project:proj_123] 模型调用开始 request_id=req_456 model=deepseek-chat detail={"request_id":"req_456","model_provider":"openai_compatible","model_name":"deepseek-chat","endpoint":"https://api.deepseek.com/v1/chat/completions","prompt_preview":"你是一个专业的短剧编剧...","prompt_len":12500,"messages_count":2,"temperature":0.7,"max_tokens":8192}
```

### 7.3 格式规范要点

| 规范 | 说明 |
|------|------|
| **消息体使用键值对** | `model=deepseek-chat latency=150333ms`，便于 grep 提取 |
| **中括号标注上下文** | `[comprehensive_extraction]`、`[project:proj_123]`、`[task:task_789]` |
| **数字带单位** | `latency=150333ms`、`tokens=8123`、`retry=2/3` |
| **列表/字典用紧凑格式** | `output={characters=8,scenes=12}` |
| **不记录敏感信息** | API Key 脱敏为 `sk-***abc`，密码等不记录 |
| **截断大内容** | 请求/响应体截断至 2000 字符，完整内容通过 request_id 关联文件 |

---

## 八、日志轮转与清理策略

| 日志类型 | 轮转周期 | 本地保留 | 清理方式 |
|----------|----------|----------|----------|
| app.log | 每天零点 | 90 天 | loguru 自动清理 |
| error.log | 每天零点 | 90 天 | loguru 自动清理 |
| project.log | 不按日期轮转 | 90 天 | loguru 自动清理 |
| task.log | 不按日期轮转 | 90 天 | loguru 自动清理 |
| model_call.log | 不按日期轮转 | 90 天 | loguru 自动清理 |
| model_call_log 表 | 按天分区 | 1 年在线 | Beat 每天 detach + drop |
| operation_record 表 | 不轮转 | 永久 | 不清理 |

---

## 九、实现方案

### 9.1 配置项

所有日志保留时长、Redis 缓冲相关参数均通过 `app/core/config.py` 配置，支持环境变量覆盖：

```python
# app/core/config.py — 日志相关配置项

class Settings(BaseSettings):
    # ... 已有配置 ...

    # === 日志配置 ===
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL", description="日志级别")
    LOG_FILE_RETENTION: str = Field(default="90 days", env="LOG_FILE_RETENTION", description="文件日志保留时长")
    LOG_FILE_MAX_SIZE: str = Field(default="50 MB", env="LOG_FILE_MAX_SIZE", description="单文件最大大小（项目日志轮转阈值）")
    LOG_DB_RETENTION_DAYS: int = Field(default=365, env="LOG_DB_RETENTION_DAYS", description="model_call_log 表保留天数")

    # === 日志 Redis 缓冲配置 ===
    LOG_REDIS_DB: int = Field(default=1, env="LOG_REDIS_DB", description="日志专用 Redis 数据库编号（避免与业务 Redis 冲突）")
    LOG_FLUSH_INTERVAL: int = Field(default=5, env="LOG_FLUSH_INTERVAL", description="日志刷写间隔（秒）")
    LOG_FLUSH_BATCH_SIZE: int = Field(default=500, env="LOG_FLUSH_BATCH_SIZE", description="每批最大刷写条数")
    LOG_REDIS_BUFFER_MAX: int = Field(default=10000, env="LOG_REDIS_BUFFER_MAX", description="Redis 缓冲区最大长度")

    @property
    def LOG_REDIS_URL(self) -> str:
        """日志专用 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.LOG_REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.LOG_REDIS_DB}"
```

**配置项说明**：

| 配置项 | 默认值 | 环境变量 | 说明 |
|--------|--------|----------|------|
| `LOG_FILE_RETENTION` | `90 days` | `LOG_FILE_RETENTION` | 所有文件日志保留时长 |
| `LOG_FILE_MAX_SIZE` | `50 MB` | `LOG_FILE_MAX_SIZE` | 项目日志单文件最大大小（超过后轮转） |
| `LOG_DB_RETENTION_DAYS` | `365` | `LOG_DB_RETENTION_DAYS` | model_call_log 分区表保留天数（1年） |
| `LOG_REDIS_DB` | `1` | `LOG_REDIS_DB` | 日志专用 Redis 库编号 |
| `LOG_FLUSH_INTERVAL` | `5` | `LOG_FLUSH_INTERVAL` | Beat 刷写间隔（秒） |
| `LOG_FLUSH_BATCH_SIZE` | `500` | `LOG_FLUSH_BATCH_SIZE` | 每批最大刷写条数 |
| `LOG_REDIS_BUFFER_MAX` | `10000` | `LOG_REDIS_BUFFER_MAX` | Redis 缓冲区最大长度 |

### 9.2 日志配置（loguru）

```python
# app/core/logging.py

import os
import sys
import json
from datetime import datetime
from loguru import logger
from app.core.config import settings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BACKEND_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# 移除默认配置
logger.remove()

# === 通用格式 ===
HUMAN_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{module}.{name}:{function}:{line} - "
    "{message}"
)

# === 1. 控制台输出 ===
logger.add(
    sys.stderr,
    format=HUMAN_FORMAT,
    level=settings.LOG_LEVEL,
    backtrace=True,
    diagnose=True,
)

# === 2. 公共应用日志 ===
logger.add(
    os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.log"),
    format=HUMAN_FORMAT,
    rotation="00:00",
    retention=settings.LOG_FILE_RETENTION,
    compression="zip",
    enqueue=True,
    level="INFO",
    backtrace=True,
    diagnose=True,
)

# === 3. 公共错误日志 ===
logger.add(
    os.path.join(LOG_DIR, "error_{time:YYYY-MM-DD}.log"),
    format=HUMAN_FORMAT,
    rotation="00:00",
    retention=settings.LOG_FILE_RETENTION,
    compression="zip",
    enqueue=True,
    level="ERROR",
    backtrace=True,
    diagnose=True,
)
```

### 9.3 项目日志管理器

```python
# app/core/project_logger.py

import os
import json
from loguru import logger
from app.core.logging import LOG_DIR, HUMAN_FORMAT

# 已创建的项目日志 sink 缓存，避免重复添加
_project_sinks: dict[str, dict] = {}


def get_project_logger(project_id: str) -> "ProjectLogger":
    """获取项目日志记录器"""
    return ProjectLogger(project_id)


class ProjectLogger:
    """项目日志管理器"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = os.path.join(LOG_DIR, "projects", project_id)
        os.makedirs(self.project_dir, exist_ok=True)
        self._sink_ids: list[int] = []

        # 首次使用时注册项目专属 sink
        if project_id not in _project_sinks:
            self._register_sinks()

    def _register_sinks(self):
        """注册项目日志 sink"""
        prefix = f"[project:{self.project_id}]"

        # project.log - 项目运行日志
        sink_id = logger.add(
            os.path.join(self.project_dir, "project.log"),
            format=HUMAN_FORMAT,
            rotation=settings.LOG_FILE_MAX_SIZE,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            enqueue=True,
            level="INFO",
            filter=lambda record: prefix in record["message"],
        )
        self._sink_ids.append(sink_id)

        # task.log - 任务执行日志
        sink_id = logger.add(
            os.path.join(self.project_dir, "task.log"),
            format=HUMAN_FORMAT,
            rotation=settings.LOG_FILE_MAX_SIZE,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            enqueue=True,
            level="INFO",
            filter=lambda record: f"[task:" in record["message"] and prefix in record["message"],
        )
        self._sink_ids.append(sink_id)

        # model_call.log - 模型调用日志（人类可读，详细JSON在message字段）
        sink_id = logger.add(
            os.path.join(self.project_dir, "model_call.log"),
            format=HUMAN_FORMAT,
            rotation=settings.LOG_FILE_MAX_SIZE,
            retention=settings.LOG_FILE_RETENTION,
            compression="zip",
            enqueue=True,
            level="INFO",
            filter=lambda record: record["extra"].get("log_type") == "model_call",
        )
        self._sink_ids.append(sink_id)

        _project_sinks[self.project_id] = {"sink_ids": self._sink_ids}

    def info(self, msg: str, **kwargs):
        logger.bind(**kwargs).info(f"[project:{self.project_id}] {msg}")

    def error(self, msg: str, **kwargs):
        logger.bind(**kwargs).error(f"[project:{self.project_id}] {msg}")

    def warning(self, msg: str, **kwargs):
        logger.bind(**kwargs).warning(f"[project:{self.project_id}] {msg}")

    def task_log(self, task_id: str, task_type: str, msg: str, **kwargs):
        logger.bind(**kwargs).info(
            f"[project:{self.project_id}] [task:{task_id}] [{task_type}] {msg}"
        )

    def model_call(self, msg: str, detail: dict):
        """记录模型调用日志（人类可读，详细JSON在message字段）"""
        detail_json = json.dumps(detail, ensure_ascii=False, default=str)
        logger.bind(log_type="model_call").info(
            f"[project:{self.project_id}] {msg} detail={detail_json}"
        )
```

### 9.4 模型调用日志写入器（含 Redis 降级方案）

```python
# app/core/model_call_log_writer.py

import json
import logging
import redis
from datetime import datetime
from loguru import logger
from app.core.config import settings


class ModelCallLogWriter:
    """模型调用日志写入器 - Redis 缓冲 + 批量写入 PG，Redis 不可用时降级直写 PG"""

    BUFFER_KEY = "log:buffer:model_call"

    def __init__(self):
        self._redis: redis.Redis | None = None
        self._redis_available: bool = True  # Redis 可用状态标记

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                settings.LOG_REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
        return self._redis

    def _check_redis(self) -> bool:
        """检查 Redis 是否可用"""
        try:
            self.redis.ping()
            self._redis_available = True
            return True
        except (redis.ConnectionError, redis.TimeoutError, Exception):
            self._redis_available = False
            logger.warning("日志 Redis 不可用，降级为直接写入 PG")
            return False

    def write(self, record: dict):
        """写入日志记录：优先 Redis 缓冲，不可用时降级直写 PG"""
        if "call_time" not in record:
            record["call_time"] = datetime.utcnow().isoformat()
        record["create_time"] = datetime.utcnow().isoformat()

        if self._redis_available:
            try:
                pipe = self.redis.pipeline()
                pipe.lpush(self.BUFFER_KEY, json.dumps(record, ensure_ascii=False, default=str))
                pipe.ltrim(self.BUFFER_KEY, 0, settings.LOG_REDIS_BUFFER_MAX - 1)
                pipe.execute()
                return
            except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
                logger.warning(f"日志写入 Redis 失败，降级直写 PG error={e}")
                self._redis_available = False

        # Redis 不可用，降级直接写入 PG
        self._write_direct_to_pg(record)

    def _write_direct_to_pg(self, record: dict):
        """降级方案：直接写入 PG（单条）"""
        from app.db.session import SessionLocal
        from app.models.model_call_log import ModelCallLog

        session = SessionLocal()
        try:
            obj = ModelCallLog(**record)
            session.add(obj)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"日志降级直写 PG 失败，日志可能丢失 error={e} record_id={record.get('id')}")
        finally:
            session.close()

    def flush_to_db(self, batch_size: int = None) -> int:
        """从 Redis 批量写入 PG（由 Beat 定时调用）"""
        if not self._redis_available:
            if not self._check_redis():
                return 0

        batch_size = batch_size or settings.LOG_FLUSH_BATCH_SIZE
        from app.db.session import SessionLocal
        from app.models.model_call_log import ModelCallLog

        records = []
        for _ in range(batch_size):
            try:
                raw = self.redis.rpop(self.BUFFER_KEY)
            except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
                self._redis_available = False
                logger.warning(f"日志刷写时 Redis 断开，停止本次刷写 error={e}")
                break
            if raw is None:
                break
            records.append(json.loads(raw))

        if not records:
            return 0

        session = SessionLocal()
        try:
            objs = [ModelCallLog(**r) for r in records]
            session.bulk_save_objects(objs)
            session.commit()
            return len(records)
        except Exception as e:
            session.rollback()
            # 写入失败，推回 Redis（如果可用）
            if self._redis_available:
                for r in records:
                    try:
                        self.redis.lpush(self.BUFFER_KEY, json.dumps(r, ensure_ascii=False, default=str))
                    except Exception:
                        pass  # 推回也失败则丢失
            logger.error(f"日志批量写入 PG 失败 error={e} count={len(records)}")
            raise
        finally:
            session.close()


# 全局单例
model_call_log_writer = ModelCallLogWriter()
```

**Redis 降级方案说明**：

| 场景 | 处理方式 |
|------|----------|
| Redis 正常 | 数据写入 Redis 缓冲区，Beat 定时批量刷写到 PG |
| Redis 连接失败 | 标记不可用，每次调用直接写入 PG（单条 INSERT） |
| Redis 恢复 | flush_to_db 时 ping 检测恢复，切回 Redis 缓冲模式 |
| PG 写入失败 | 数据推回 Redis（如果 Redis 可用），否则记录错误日志 |

### 9.5 模型调用层集成（日志装饰器）

### 9.4 模型调用层集成（日志装饰器）

```python
# 在 TextModelProvider.generate 中集成日志记录

def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=8192,
             timeout=180, user_id=None, project_id=None, task_id=None):
    """调用文本模型，自动记录日志"""
    request_id = generate_id()

    # 构建日志记录
    log_record = {
        "user_id": user_id or "system",
        "project_id": project_id,
        "task_id": task_id,
        "request_id": request_id,
        "model_provider": "openai_compatible",
        "model_name": self.model_name,
        "endpoint": f"{self.client.base_url}/chat/completions",
        "api_key_masked": self._mask_api_key(settings.LLM_API_KEY),
        "request_body": {
            "prompt_preview": prompt[:2000],
            "messages_count": 1 + (1 if system_prompt else 0),
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    }

    call_time = datetime.utcnow()
    start = time.monotonic()
    try:
        response = self.client.chat.completions.create(...)
        content = response.choices[0].message.content
        usage = response.usage
        latency_ms = int((time.monotonic() - start) * 1000)

        # 通用 Usage 字段
        log_record.update({
            "call_time": call_time.isoformat(),  # 模型实际调用时间
            "provider_request_id": getattr(response, "id", None),  # 模型厂商请求ID
            "response_status": 200,
            "response_body": {"result_preview": content[:2000]},
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "latency_ms": latency_ms,
            # 供应商特有 Usage
            "usage_details": self._extract_usage_details(usage),
        })

        # 写入日志（Redis 缓冲 + 文件）
        model_call_log_writer.write(log_record)
        if project_id:
            get_project_logger(project_id).model_call(
                f"模型调用完成 request_id={request_id} model={self.model_name} "
                f"status=200 input_tokens={log_record['input_tokens']} "
                f"output_tokens={log_record['output_tokens']} "
                f"total_tokens={log_record['total_tokens']} latency={latency_ms}ms",
                log_record,
            )

        return ModelResult(content=content, ...)

    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        log_record.update({
            "call_time": call_time.isoformat(),
            "latency_ms": latency_ms,
            "error_message": str(e),
        })
        model_call_log_writer.write(log_record)
        raise
```

### 9.6 Beat 定时刷写任务

```python
# app/tasks/log_flush.py

@celery_app.task(name="log.flush_model_call_log")
def flush_model_call_log():
    """定时从 Redis 缓冲区批量写入 model_call_log 表"""
    count = model_call_log_writer.flush_to_db()
    if count > 0:
        logger.info(f"模型调用日志刷写完成 count={count}")
```

---

