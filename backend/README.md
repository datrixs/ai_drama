# 皮皮虾短剧 · 后端服务

## 一、环境要求

- Python >= 3.12
- PostgreSQL >= 15
- Redis >= 5
- ffmpeg >= 4（视频拼接与封面帧提取用，需安装并加入 PATH）

## 二、安装

### 1. 创建虚拟环境

由于管理虚拟环境的工具很多，以 venv 为例。
将全局 python 切换为 3.12 版本，进入 backend 目录，执行创建虚拟环境命令：

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
```

出现下图中 `(.venv)` 表示虚拟环境已激活。
**注意：后续命令都需要在虚拟环境下执行。**

![alt text](docs/images/venv.png)

### 2. 安装 python 依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 创建配置文件（.env 文件）

```bash
Copy-Item ".env.example" ".env"   # Windows
# cp .env.example .env            # Linux / macOS
```

按需修改 `.env` 中的数据库连接、Redis 连接与各模型平台密钥。

## 三、初始化数据库

#### 1. 创建数据库

通过数据库可视化管理工具（pgAdmin / DBeaver / psql）创建数据库，数据库名称为 `pipixia-drama`。

#### 2. 导入表结构与初始数据（二选一）

**方式 A：导入初始 SQL（推荐）**

在项目根目录执行：

```bash
psql -U postgres -d "pipixia-drama" -f sql/init.sql
```

**方式 B：执行初始化脚本**（自动建表并写入全部初始数据）

```bash
cd backend
python .\scripts\init_db.py
```

初始化完成后，默认账号：

- 用户名：`test`
- 密码：`123456`

## 四、启动服务

#### 1. 启动 API 服务

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### 2. 启动 Celery（AI 生成等异步任务依赖）

```bash
# Worker
celery -A app.core.celery worker --loglevel=info -E -P gevent -c 100

# 定时任务
celery -A app.core.celery beat --loglevel=info

# 任务监控面板（可选）
celery -A app.core.celery flower --port=5555
```

## 五、常用脚本

| 脚本 | 说明 |
|------|------|
| `scripts/init_db.py` | 建表并写入全部初始数据（默认用户、模型、计费、会员等） |
| `scripts/seed_membership.py` | 单独初始化会员等级/权益/积分套餐（`init_db.py` 已包含，存量库可单独补数） |
| `scripts/gen_init_sql.py` | 数据模型变更后重新生成根目录 `sql/init.sql` |
| `scripts/pg_backup.sh` | PostgreSQL 数据库备份 |
