# Samoyed

Samoyed 是一个面向技术研究所和研发 Lab 的可配置研究助手框架。它每天从公开新闻、论文、会议、专利和企业资料中发现新信号，经过去重、相关性判断和 AI 分析后，形成：

- 研究所公共 Dashboard：今天发生了什么？
- Lab 专属 My Lab：哪些变化与当前 Lab 有关？为什么相关？会影响什么判断？
- 文章详情：原文、作者、来源、链接、AI 判断和 Lab 参考
- AI 洞察报告：按 Lab 汇总今日和本月的重要变化

项目的产品方向不是资料上传或 Document AI，而是可替换数据源和 AI Provider 的 Research Feed：

```text
公开来源
  -> 采集
  -> 去重
  -> 资料标准化
  -> AI / 规则相关性判断
  -> 公共变化
  -> Lab Profile 匹配
  -> Lab 专属解释
  -> Dashboard / My Lab / 洞察报告
```

## 当前能力

### 研究信息

- 2026 年资料抓取和过滤
- 按文章发布日期划分“今日新增”和“本月新增”
- 没有发布日期的资料不会进入今日或本月列表
- 企业新闻、学术论文、会议、专利新闻和其他技术信息分类
- 保留原始标题、正文或摘要、作者、来源、原文链接和发布时间
- 去重支持 canonical URL 和内容指纹

### Lab 工作流

项目包含一组用于本地演示的公开技术领域示例数据。生产环境应删除或替换这些 demo seed，并为每个 Lab 配置独立的：

- 研究定位
- 企业关注对象
- 高校和教授关注对象
- 学术会议和技术主题
- Lab 相关变化
- “为什么相关”和“判断影响”

### 用户和权限

- Google OAuth 登录
- 系统管理员
- Lab 管理员
- Lab 用户
- 游客
- 系统管理员可以管理 Lab、成员、邀请、自动运行和数据来源
- Lab 管理员可以配置所属 Lab 的关注对象
- 游客只能查看公共 Dashboard

### AI 能力

AI 通过可替换的 AI Gateway 接入，支持：

- Dify Workflow
- OpenAI Responses API
- Rule-based fallback
- AI 网页检索
- 文章中英日翻译
- 文章相关性判断、摘要、变化判断和重要性判断
- Lab 专属解释和洞察报告

AI 输出必须被视为研究辅助结果，而不是事实、投资建议或工程结论。系统会标记 Dify/DeepSeek 生成结果与规则降级结果，并尽量保留来源链接和检索状态。

当 AI 服务不可用时，系统可以使用规则分析继续完成基础数据流转。页面会显示当前判断是 AI 生成还是规则结合 Lab 范围生成。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| Web | Next.js 16、React 19、TypeScript |
| API | FastAPI、Python、Pydantic |
| ORM | SQLAlchemy 2 |
| 数据库 | PostgreSQL 16；本地直跑也支持 SQLite |
| 迁移 | Alembic |
| 缓存和任务基础设施 | Redis |
| 对象存储基础设施 | MinIO |
| 登录 | Google OAuth 2.0 |
| AI | Dify、OpenAI、规则分析 fallback |
| 部署基础 | Docker Compose，可继续部署到 AWS |

## 快速启动：Docker Compose

### 1. 准备环境

需要安装：

- Docker Desktop
- Docker Compose
- Git

### 2. 配置环境变量

```bash
cp .env.example .env
```

至少修改：

```env
POSTGRES_PASSWORD=修改为强密码
MINIO_ROOT_PASSWORD=修改为强密码
SECRET_KEY=生成一个足够长的随机字符串
```

如果暂时不接入登录和 AI，可以先保留以下默认值：

```env
AI_PROVIDER=rule_based
OPENAI_API_KEY=
DIFY_API_KEY=
DIFY_SEARCH_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
ADMIN_EMAILS=
```

### 3. 启动

```bash
docker compose up --build
```

访问：

- Web：http://localhost:3000
- API：http://localhost:8000
- 健康检查：http://localhost:8000/health
- 就绪检查：http://localhost:8000/health/ready
- Swagger API 文档：http://localhost:8000/docs
- MinIO Console：http://localhost:9001

API 容器启动时会自动执行：

```bash
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

默认 seed 只创建基础运行配置，不导入任何 Lab、文章或领域数据。若要在本地演示使用示例数据，显式设置 `SEED_DEMO_DATA=true`；示例数据位于 `services/api/examples/demo_seed.py`，不应直接用于生产。

### 停止和清理

停止容器但保留数据：

```bash
docker compose down
```

停止容器并删除 PostgreSQL、Redis、MinIO 数据卷：

```bash
docker compose down -v
```

第二个命令会删除本地开发数据，请谨慎使用。

## 本地开发

### API

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

touch local.env
cat >> local.env <<'EOF'
DATABASE_URL=sqlite+pysqlite:////private/tmp/research-radar-preview.db
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_SECURE=false
EOF
set -a
source local.env
set +a

alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果使用 SQLite，本地环境可以配置：

```env
DATABASE_URL=sqlite+pysqlite:////private/tmp/research-radar-preview.db
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

默认访问 http://localhost:3000。

Web 端支持以下 API 地址变量：

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
API_INTERNAL_BASE_URL=http://127.0.0.1:8000
```

Docker 中 `API_INTERNAL_BASE_URL` 应指向 `http://api:8000`，浏览器端的 `NEXT_PUBLIC_API_BASE_URL` 应指向浏览器可以访问的地址。

## 环境变量

完整模板见 `.env.example`。主要变量如下：

### 数据库和基础设施

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy 数据库连接串；Docker 会自动覆盖为 PostgreSQL |
| `POSTGRES_DB` | PostgreSQL 数据库名 |
| `POSTGRES_USER` | PostgreSQL 用户 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 |
| `REDIS_URL` | Redis 地址 |
| `MINIO_ENDPOINT` | MinIO 地址 |
| `MINIO_ROOT_USER` | MinIO 管理员用户名 |
| `MINIO_ROOT_PASSWORD` | MinIO 管理员密码 |
| `SECRET_KEY` | 应用会话和安全配置使用的密钥 |

### AI

| 变量 | 说明 |
| --- | --- |
| `AI_PROVIDER` | 文章分析使用的 provider：`rule_based`、`deepseek`、`openai`、`dify` 或 `auto` |
| `ASSISTANT_PROVIDER` | Snowy 助手使用的 provider；默认 `deepseek`，以后切换助手模型只改这里 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key；Snowy Agent 使用 |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址，默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | DeepSeek 模型名称 |
| `DEEPSEEK_MAX_TOOL_TURNS` | Snowy Agent 单次最多调用研究工具的轮数 |
| `ASSISTANT_WEB_SEARCH_ENABLED` | 是否允许 Snowy 在 Lab 数据不足时搜索公开网页，默认 `true` |
| `OPENAI_API_KEY` | OpenAI API Key |
| `OPENAI_MODEL` | OpenAI Responses API 使用的模型 |
| `OPENAI_AI_SEARCH_ENABLED` | 是否允许 AI 网页检索 |
| `DIFY_BASE_URL` | Dify API 地址 |
| `DIFY_API_KEY` | 文章分析 Workflow 的 API Key |
| `DIFY_SEARCH_API_KEY` | 网页检索 Workflow 的 API Key |
| `DIFY_USER` | Dify 请求使用的 user 标识 |
| `PATENTSVIEW_API_KEY` | PatentsView PatentSearch API Key；未配置时该来源显示为“需 API Key” |

### 登录

| 变量 | 说明 |
| --- | --- |
| `GOOGLE_CLIENT_ID` | Google OAuth Web Application Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | OAuth 回调地址 |
| `FRONTEND_URL` | 登录成功后的前端地址 |
| `ADMIN_EMAILS` | 系统管理员邮箱，多个邮箱用逗号分隔 |

本地回调地址示例：

```text
http://127.0.0.1:8000/api/auth/google/callback
```

生产环境必须替换为 HTTPS 域名，并在 Google Cloud OAuth 配置中加入完全一致的回调地址。

## Dify 配置

Dify 配置文档见 [`docs/DIFY_WORKFLOW_SETUP.md`](docs/DIFY_WORKFLOW_SETUP.md)。

需要创建两个已发布的 Workflow：

1. `Research Radar Analyzer`
2. `Research Radar Search`

两个 Workflow 都需要接收：

- `prompt`
- `schema_name`
- `schema`

并通过 End 节点返回名为 `result` 的 JSON 文本。

配置完成后设置：

```env
AI_PROVIDER=dify
DIFY_API_KEY=你的分析工作流密钥
DIFY_SEARCH_API_KEY=你的检索工作流密钥
```

检查：

```bash
curl http://localhost:8000/api/ai/status
curl http://localhost:8000/api/ai/dify/check
```

注意：AI 分析是外部网络调用。Dify 响应慢或不可用时，系统会回退到规则分析；生产环境建议为抓取和 AI 分析拆分任务队列，并配置超时、重试和限流。

## 数据来源和时间口径

来源配置位于 `services/api/app/db/seed.py`，当前覆盖：

- arXiv
- Crossref
- OpenAlex
- Semantic Scholar
- Europe PMC
- Google News RSS
- Google Patents 尝试接口
- PatentsView（需要 `PATENTSVIEW_API_KEY`）
- Intel Newsroom
- Samsung Electro-Mechanics
- IMAPS
- Nippon Electric Glass
- Micron、TSMC、NVIDIA 相关公开新闻检索

管理员控制台的“数据来源”区域会显示每个来源的：

- 来源类型
- 来源地址
- 已入库资料数量
- 最新发布日期
- 最近抓取时间
- 当前状态

时间规则：

- 今日新增：发布日期属于今天
- 本月新增：发布日期属于本月 1 号到昨天
- 其他月份：暂不展示在今日和本月列表
- 没有发布日期：不进入今日和本月列表
- 抓取时间只用于追踪采集状态，不用于判断文章属于哪一天

执行一次来源抓取：

```bash
curl -X POST http://localhost:8000/api/ingest/run
```

执行完整雷达流程：

```bash
curl -X POST http://localhost:8000/api/radar/run
```

完整流程包含来源抓取、AI 网页检索、待处理资料分析和变化生成。Dify 运行较慢时，建议先单独抓取，再单独运行分析：

```bash
curl -X POST http://localhost:8000/api/ingest/run
curl -X POST http://localhost:8000/api/analyze/run
```

## 主要页面

| 页面 | 说明 |
| --- | --- |
| `/` | 公共 Dashboard、今日热点和本月新增 |
| `/labs/{lab_id}` | Lab 专属变化、关注对象和 Lab 判断 |
| `/labs/{lab_id}/report` | Lab AI 洞察报告和打印视图 |
| `/labs/{lab_id}/settings` | Lab 关注对象配置，管理员可用 |
| `/changes/{change_id}` | 原文、作者、来源、链接、AI 判断和 Lab 参考 |
| `/admin` | 来源、Lab、成员、自动运行和雷达执行记录 |

文章详情支持单篇切换：

- English
- 中文
- 日本語

系统头像菜单支持独立的系统语言和亮色 / 深色页面风格设置。

## API 速查

### 公共数据

```text
GET /api/changes/today
GET /api/changes/month
GET /api/changes/{change_id}
GET /api/documents/{document_id}
GET /api/labs
GET /api/labs/{lab_id}
GET /api/labs/{lab_id}/changes/today
GET /api/labs/{lab_id}/changes/month
GET /api/labs/{lab_id}/watch-items
GET /api/translations/{change_id}?locale=zh|en|ja
```

### 管理和运行

```text
GET  /api/admin/sources
GET  /api/admin/schedule
PUT  /api/admin/schedule
GET  /api/radar/runs
POST /api/radar/run
POST /api/ingest/run
POST /api/analyze/run
GET  /api/analyses/recent
GET  /api/ai/status
GET  /api/ai/dify/check
```

完整接口可以直接查看 FastAPI Swagger：`/docs`。

## 数据库迁移和种子数据

迁移目录：`services/api/migrations/versions/`

执行迁移：

```bash
cd services/api
alembic upgrade head
```

初始化或补充种子数据：

```bash
PYTHONPATH=. python -m app.db.seed
```

核心表包括：

- `labs`
- `lab_profiles`
- `sources`
- `documents`
- `analyses`
- `entity_states`
- `changes`
- `lab_change_interpretations`
- `watch_items`
- `lab_watch_items`
- `users`
- `lab_memberships`
- `radar_runs`
- `radar_settings`

## 测试和质量检查

后端单元测试与 API 测试：

```bash
cd services/api
.venv/bin/pytest -q
```

前端类型检查和生产构建：

```bash
cd apps/web
npm test
npm run build
```

基础 Python 编译检查：

```bash
python -m compileall services/api/app
```

## 项目结构

```text
.
├── apps/web/                 # Next.js Web 应用
│   └── app/                  # Dashboard、My Lab、详情、管理页面
├── services/api/             # FastAPI 服务
│   ├── app/api/              # HTTP API 路由
│   ├── app/db/               # SQLAlchemy 模型和种子数据
│   ├── app/services/         # 抓取、分析、AI、认证和雷达流程
│   ├── migrations/           # Alembic 迁移
│   └── tests/                # 后端测试
├── database/schema.sql       # 数据库结构参考
├── docs/                     # 产品、架构、Dify 配置和任务文档
├── docker-compose.yml        # PostgreSQL、Redis、MinIO、API、Web
└── .env.example              # 环境变量模板
```

## AWS 部署建议

当前 Docker Compose 适合本地开发和早期验证。部署到 AWS 时建议拆分为：

- Web：ECS Fargate 或 AWS App Runner
- API：ECS Fargate
- PostgreSQL：Amazon RDS for PostgreSQL
- Redis：Amazon ElastiCache for Redis
- 对象存储：Amazon S3
- 定时任务：EventBridge Scheduler + ECS Task，或 EventBridge + SQS Worker
- 密钥：AWS Secrets Manager 或 Systems Manager Parameter Store
- 域名和 HTTPS：Application Load Balancer + ACM + Route 53
- 日志：CloudWatch Logs

生产环境至少需要：

1. 使用 RDS，不使用容器内数据库。
2. 使用 Secrets Manager 管理 OAuth、Dify、OpenAI 和数据库密钥。
3. 配置 HTTPS，并更新 Google OAuth 回调地址。
4. 将抓取、AI 分析和页面 API 拆成可独立扩缩容的任务。
5. 设置抓取超时、重试、速率限制和失败告警。
6. 将数据库迁移作为发布流程的一部分执行。
7. 为来源、文档、分析和变化建立日志与运行记录。
8. 不把 `.env`、`local.env`、数据库文件和云平台密钥提交到 Git。

## 当前边界

当前版本暂不包含：

- 用户上传资料
- OCR 和 PDF 管理流程
- 多租户计费
- 完整的后台来源编辑器
- 专利数据的稳定多源 API 兜底
- AI 分析任务队列和并发调度
- 生产级审计日志和细粒度组织权限

这些能力可以在数据源稳定、Lab 使用流程验证后继续建设。
