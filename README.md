<div align="center">

<!-- Logo 占位：请将项目 Logo 放置到 docs/images/logo.png 后取消下行注释 -->
<!-- <img src="docs/images/logo.png" width="180" alt="皮皮虾短剧 Logo"> -->

# 🎬 皮皮虾短剧（Pipixia Drama）

### 基于 AI 的短剧制作平台 —— 从小说到成片，一站完成

**简体中文** | [English](README.en.md)

**🌐 在线体验：[https://www.datrix.com.cn/](https://www.datrix.com.cn/)**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7%2B-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5-37814A?style=flat-square&logo=celery&logoColor=white)](https://docs.celeryq.dev/)

从小说文本出发，AI 自动完成剧情大纲、人物关系、场景与道具分析，
在此基础上进行分镜编排、角色/场景/道具图片生成、配音、视频生成与超分辨率处理，
最终制作成完整的短剧视频。

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [使用截图](#-使用截图) · [配置说明](#%EF%B8%8F-配置说明) · [参与贡献](#-参与贡献)

<img src="docs/screenshots/overview.png" alt="皮皮虾短剧平台首页">

</div>

---

## ✨ 功能特性

### 📖 智能剧本创作
- **小说智能分析**：粘贴小说文本，AI 自动生成剧情大纲、人物特征与人物关系、场景描写、道具清单
- **分镜编辑器**：按场次/分镜组织故事，支持对每条分镜的台词、画面描述进行编辑与重新生成
- **画布编辑器**：节点式自由创作画布，图片/视频生成节点可编排组合

### 🎨 AI 生成能力
- **图片生成**：角色、场景、道具图片生成，支持角色一致性控制与参考图
- **视频生成**：文生视频 / 图生视频，支持「全能参考」（图片+视频参考素材）
- **语音合成**：文本转语音与声音设计，支持语速调节
- **视频超分**：生成结果可提升至 720P / 1080P / 2K / 4K

### 🗂️ 资产与协作
- **资产中心**：图片、音频、视频资产统一管理，跨项目复用，支持主账号资产共享给子账号
- **多用户体系**：主账号 + 子账号，细粒度操作权限（项目 / 资产的增删改查）
- **任务系统**：Celery 异步任务队列 + Flower 监控面板，生成任务全程可追踪（WebSocket / SSE 实时推送）

### 💰 运营能力（可选）
- **积分计费**：按模型/分辨率/时长的积分计费体系，双账户余额（赠送/充值）
- **会员体系**：会员等级、权益配置、积分充值套餐
- **支付对接**：内置杉德支付充值模块（可配置关闭）

### ⚙️ 灵活配置
- **多模型接入**：火山方舟（Doubao / Seedream / Seedance）、DeepSeek、GPT 系列图片模型、阿里百炼语音等，密钥与模型均可配置
- **项目级配置**：每个项目可独立设置模型、分辨率、画风、并发数等，支持配置继承

## 📸 使用截图

### 故事分析
粘贴小说文本，AI 自动生成剧情大纲、人物小传、人物关系、场景与道具
![故事分析](docs/screenshots/analysis.png)

### 分镜编辑器
按场次/分镜组织故事，支持台词与画面描述编辑、生成结果实时预览
![分镜编辑器](docs/screenshots/storyboard.png)

### 无限画布
节点式自由创作画布，图片/视频生成节点可编排组合
![无限画布](docs/screenshots/canvas.png)

### 剧集生成
分镜视频自动合成剧集，支持重新生成与进入制片
![剧集生成](docs/screenshots/video-gen.png)

### 产品资产
项目内角色/场景资产分组管理，生成结果可复用
![产品资产](docs/screenshots/product-assets.png)

### 资产中心
图片、音频、视频资产统一管理，跨项目复用与共享
![资产中心](docs/screenshots/assets.png)

## 🏗️ 技术架构

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite |
| 后端 | FastAPI + SQLAlchemy 2.0 |
| 数据库 | PostgreSQL 15+ |
| 缓存 / 队列 | Redis 7+ + Celery（Worker / Beat / Flower） |
| 实时通信 | WebSocket / SSE |
| 对象存储 | 腾讯云 COS（可替换） |
| AI 模型 | 火山方舟 Ark、DeepSeek、GPT 图片模型、阿里百炼（语音）等 |

```
┌─────────────┐     ┌──────────────────────────────────────────┐
│   Vue 3 前端  │────▶│                FastAPI 后端                │
└─────────────┘     │  ┌────────┐ ┌────────┐ ┌──────────────┐   │
     WebSocket/SSE  │  │ 业务API │ │ Auth │ │  AI 编排服务   │   │
                    │  └───┬────┘ └───┬────┘ └──────┬───────┘   │
                    └──────┼──────────┼─────────────┼───────────┘
                           ▼          ▼             ▼
                    ┌──────────┐ ┌────────┐ ┌──────────────┐
                    │PostgreSQL│ │ Redis  │ │Celery Workers │
                    └──────────┘ └────────┘ └──────┬───────┘
                                                  ▼
                                    ┌─────────────────────────┐
                                    │ AI 模型 / COS 对象存储 / 超分 │
                                    └─────────────────────────┘
```

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.12 | 后端运行时 |
| Node.js | >= 18 | 前端构建 |
| PostgreSQL | >= 15 | 主数据库 |
| Redis | >= 5 | 缓存与消息队列 |
| ffmpeg | >= 4 | 视频拼接与封面帧提取，需安装并加入 PATH |

### 1. 启动 PostgreSQL 与 Redis

使用 Docker 快速启动（已有环境可跳过）：

```bash
docker run -d --name pipixia-pg -p 5432:5432 \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres \
  postgres:15

docker run -d --name pipixia-redis -p 6379:6379 redis:7
```

### 2. 初始化数据库

创建数据库 `pipixia-drama` 后，**二选一**完成表结构与初始数据导入：

**方式 A：导入初始 SQL（推荐，无需安装后端依赖）**

```bash
psql -U postgres -d "pipixia-drama" -f sql/init.sql
```

**方式 B：执行初始化脚本**（见 [后端详细指南](backend/README.md)，需先完成后端依赖安装）

```bash
cd backend
python scripts/init_db.py
```

### 3. 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt

copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS
# 按需修改 .env 中的数据库连接与各模型密钥

uvicorn main:app --host 0.0.0.0 --port 8000
```

AI 生成任务依赖 Celery，另开终端启动 Worker 与定时任务：

```bash
cd backend
celery -A app.core.celery worker --loglevel=info -P gevent -c 100
celery -A app.core.celery beat --loglevel=info
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000`（开发服务器会将 `/api` 请求代理到 `http://127.0.0.1:8000`，请确保后端已启动），使用默认账号登录：

| 账号 | 密码 |
|------|------|
| `test` | `123456` |

> ⚠️ 生产环境请务必修改默认账号密码与 `SECRET_KEY`。

## ⚙️ 配置说明

后端配置文件为 `backend/.env`（从 `.env.example` 复制），关键配置：

| 配置项 | 必填 | 说明 |
|--------|------|------|
| `SECRET_KEY` | ✅ | JWT 签名密钥，请更换为随机字符串 |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | ✅ | PostgreSQL 连接信息 |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` | ✅ | Redis 连接信息 |
| `DEFAULT_USER_NAME` / `DEFAULT_USER_PASSWORD` | ✅ | 初始化脚本创建的默认账号 |
| `TENCENT_COS_*` | 建议 | 腾讯云 COS 对象存储（图片/视频/音频存储） |
| `VOLC_ACCESSKEY` / `VOLC_SECRETKEY` | 按需 | 火山引擎密钥（Doubao / Seedream / Seedance） |
| `VOLC_OVERSEA_*` | 按需 | BytePlus（海外）密钥 |
| `CALLBACK_BASE_URL` | 按需 | 视频生成回调地址（公网部署时必填） |
| `SANDPAY_*` | 按需 | 杉德支付商户配置（不开通充值可不填） |

> 完整配置项说明见 [backend/.env.example](backend/.env.example) 内注释。

## 📖 文档

- [后端详细指南](backend/README.md) —— 环境安装、数据库初始化、服务启动
- [技术设计](docs/tech/) —— 架构与详细设计文档

## 🤝 参与贡献

欢迎通过 Issue 反馈问题、提交 PR 参与开发：

1. Fork 本仓库并创建特性分支
2. 提交遵循现有代码风格的改动
3. 创建 Pull Request 并描述变更内容

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。
