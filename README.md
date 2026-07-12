# Samoyed

Samoyed 是一个面向技术研究所、研发团队和 Research Lab 的开源研究信号雷达。

它从公开新闻、论文、会议、专利和企业资料中持续发现新变化，经过标准化、去重、相关性判断和 AI 分析后，帮助团队回答三个问题：

- 今天发生了什么？
- 哪些变化与我的 Lab 有关？
- 这些变化会如何影响当前的研究判断？

Samoyed 的核心不是资料上传或 Document AI，而是一条可替换的数据与 AI 流水线：

~~~text
公开来源
  → 采集
  → 去重与标准化
  → AI / 规则分析
  → 公共研究变化
  → Lab Profile 匹配
  → Lab 专属解释
  → Dashboard / My Lab / 洞察报告
~~~

> 项目仍处于早期开发阶段。它适合本地研究、产品验证和二次开发，不应直接作为未经加固的生产系统使用。

## 功能概览

### 研究信息

- 按发布日期区分“今日新增”和“本月新增”
- 支持企业新闻、学术论文、会议、专利和其他技术资料
- 保留标题、摘要或正文、作者、来源、原文链接和发布时间
- 使用 canonical URL 和内容指纹进行去重
- 对来源、抓取、分析和雷达运行保留状态记录

### Lab 工作流

每个 Lab 可以独立配置：

- 研究定位和关键问题
- 企业、高校、教授、会议和技术主题
- 关注对象及其说明
- 相关变化、相关原因和判断影响

系统提供公共 Dashboard、My Lab、文章详情和 Lab 洞察报告四类主要视图。

### 用户与权限

- Google OAuth 登录
- 系统管理员、Lab 管理员、Lab 用户和游客角色
- 系统管理员可以管理 Lab、成员、邀请、来源和自动运行
- Lab 管理员可以管理所属 Lab 的关注对象和成员权限
- 游客只能访问公共 Dashboard

### AI 能力

AI 通过可替换的 Gateway 接入，目前支持：

- Dify Workflow
- OpenAI Responses API
- DeepSeek 助手
- 规则分析 fallback
- 公开网页检索
- 文章中英日翻译
- 相关性、摘要、变化、重要性和 Lab 影响判断

AI 服务不可用时，系统可以用规则分析完成基础流程。页面会标注结果来自 AI Provider，还是规则结合 Lab 范围生成。

AI 输出是研究辅助结果，不是事实认定、投资建议或工程结论。系统会尽量保留来源链接，使用者应自行核验原始资料。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| Web | Next.js 16、React 19、TypeScript |
| API | FastAPI、Python、Pydantic |
| ORM | SQLAlchemy 2 |
| 数据库 | PostgreSQL 16；本地开发支持 SQLite |
| 迁移 | Alembic |
| 缓存与基础设施 | Redis、MinIO |
| 登录 | Google OAuth 2.0 |
| AI | Dify、OpenAI、DeepSeek、规则分析 |
| 本地编排 | Docker Compose |

## 快速开始

### Docker Compose

需要先安装 Docker Desktop、Docker Compose 和 Git。

~~~bash
cp .env.example .env
~~~

至少修改开发密码和应用配置：

~~~env
POSTGRES_PASSWORD=设置一个本地开发密码
MINIO_ROOT_PASSWORD=设置一个本地开发密码
SECRET_KEY=设置一段足够长的随机字符串
~~~

如果暂时不接入 Google 登录和外部 AI，可以保留规则模式：

~~~env
AI_PROVIDER=rule_based
OPENAI_API_KEY=
DIFY_API_KEY=
DIFY_SEARCH_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
ADMIN_EMAILS=
~~~

启动全部服务：

~~~bash
docker compose up --build
~~~

服务地址：

| 服务 | 地址 |
| --- | --- |
| Web | http://localhost:3000 |
| API | http://localhost:8000 |
| 健康检查 | http://localhost:8000/health |
| 就绪检查 | http://localhost:8000/health/ready |
| Swagger | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

默认 seed 只创建基础运行配置，不会导入 Lab、文章或领域示例数据。需要演示数据时，显式设置：

~~~env
SEED_DEMO_DATA=true
~~~

示例数据位于 services/api/examples/demo_seed.py，不应直接用于生产环境。

停止服务但保留数据：

~~~bash
docker compose down
~~~

停止服务并删除本地数据卷：

~~~bash
docker compose down -v
~~~

### 本地开发

#### 启动 API

~~~bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
~~~

创建 local.env，使用 SQLite 运行本地 API：

~~~env
DATABASE_URL=sqlite+pysqlite:////private/tmp/research-radar-preview.db
REDIS_URL=redis://127.0.0.1:6379/0
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_SECURE=false
~~~

执行迁移、初始化并启动：

~~~bash
set -a
source local.env
set +a

alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

如果需要本地演示数据，设置 SEED_DEMO_DATA=true 后重新执行 seed。

#### 启动 Web

另开一个终端：

~~~bash
cd apps/web
npm install
npm run dev
~~~

默认访问 http://localhost:3000。Web 支持以下 API 地址配置：

~~~env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
API_INTERNAL_BASE_URL=http://127.0.0.1:8000
~~~

Docker 环境中，API_INTERNAL_BASE_URL 应指向 http://api:8000，而 NEXT_PUBLIC_API_BASE_URL 应指向浏览器可访问的地址。

## 配置说明

完整模板见 .env.example。

### 数据库与基础设施

| 变量 | 说明 |
| --- | --- |
| DATABASE_URL | SQLAlchemy 数据库连接串；Docker 会注入 PostgreSQL 地址 |
| POSTGRES_DB | PostgreSQL 数据库名 |
| POSTGRES_USER | PostgreSQL 用户名 |
| POSTGRES_PASSWORD | PostgreSQL 密码 |
| REDIS_URL | Redis 地址 |
| MINIO_ENDPOINT | MinIO 地址 |
| MINIO_ROOT_USER | MinIO 管理员用户名 |
| MINIO_ROOT_PASSWORD | MinIO 管理员密码 |
| SECRET_KEY | 应用安全配置使用的密钥，不应提交到 Git |
| APP_ENV | 运行环境，例如 development 或 production |

### AI

| 变量 | 说明 |
| --- | --- |
| AI_PROVIDER | 分析 Provider：rule_based、deepseek、openai、dify 或 auto |
| ASSISTANT_PROVIDER | Snowy 助手使用的 Provider，默认 deepseek |
| DEEPSEEK_API_KEY | DeepSeek API Key |
| DEEPSEEK_BASE_URL | DeepSeek API 地址 |
| DEEPSEEK_MODEL | DeepSeek 模型名称 |
| DEEPSEEK_MAX_TOOL_TURNS | Snowy 单次最多调用研究工具的轮数 |
| ASSISTANT_WEB_SEARCH_ENABLED | 是否允许 Snowy 搜索公开网页 |
| OPENAI_API_KEY | OpenAI API Key |
| OPENAI_MODEL | OpenAI 使用的模型 |
| OPENAI_AI_SEARCH_ENABLED | 是否允许 OpenAI 网页检索 |
| DIFY_BASE_URL | Dify API 地址 |
| DIFY_API_KEY | 文章分析 Workflow 的 API Key |
| DIFY_SEARCH_API_KEY | 网页检索 Workflow 的 API Key |
| DIFY_USER | Dify 请求中的 user 标识 |
| PATENTSVIEW_API_KEY | PatentsView API Key；未配置时该来源会跳过 |

### 登录

| 变量 | 说明 |
| --- | --- |
| GOOGLE_CLIENT_ID | Google OAuth Web Application Client ID |
| GOOGLE_CLIENT_SECRET | Google OAuth Client Secret |
| GOOGLE_REDIRECT_URI | OAuth 回调地址 |
| FRONTEND_URL | 登录成功后的前端地址 |
| ADMIN_EMAILS | 系统管理员邮箱，多个邮箱用逗号分隔 |

本地回调地址示例：

~~~text
http://127.0.0.1:8000/api/auth/google/callback
~~~

生产环境应使用 HTTPS，并在 Google Cloud OAuth 配置中加入完全一致的回调地址。

## Dify 配置

详细步骤见 docs/DIFY_WORKFLOW_SETUP.md。

需要创建两个已发布的 Workflow：

1. Research Radar Analyzer
2. Research Radar Search

两个 Workflow 都需要接收 prompt、schema_name 和 schema，并通过 End 节点返回名为 result 的 JSON 文本。

配置完成后：

~~~env
AI_PROVIDER=dify
DIFY_API_KEY=你的分析工作流密钥
DIFY_SEARCH_API_KEY=你的检索工作流密钥
~~~

检查连接状态：

~~~bash
curl http://localhost:8000/api/ai/status
curl http://localhost:8000/api/ai/dify/check
~~~

AI 分析是外部网络调用。Provider 响应慢或不可用时，系统会回退到规则分析；生产环境应额外配置任务队列、超时、重试、限流和失败告警。

## 数据来源与时间口径

当前示例来源覆盖：

- arXiv、Crossref、OpenAlex、Semantic Scholar、Europe PMC
- Google News RSS
- Google Patents 尝试接口和 PatentsView
- Intel Newsroom、Samsung Electro-Mechanics、IMAPS、Nippon Electric Glass
- Micron、TSMC、NVIDIA 等企业的公开信息

来源配置位于 services/api/app/db/seed.py。不同来源的 API 限制、使用条款和可保存内容可能不同，部署前应逐一核对。

时间规则如下：

- 今日新增：发布日期属于今天
- 本月新增：发布日期属于本月 1 号到昨天
- 没有发布日期的资料：不进入今日和本月列表
- 抓取时间：只用于追踪采集状态，不用于判断文章归属日期

执行一次来源抓取：

~~~bash
curl -X POST http://localhost:8000/api/ingest/run
~~~

执行完整雷达流程：

~~~bash
curl -X POST http://localhost:8000/api/radar/run
~~~

也可以拆开执行：

~~~bash
curl -X POST http://localhost:8000/api/ingest/run
curl -X POST http://localhost:8000/api/analyze/run
~~~

## 页面与 API

### 主要页面

| 页面 | 说明 |
| --- | --- |
| / | 公共 Dashboard、今日热点和本月新增 |
| /labs/{lab_id} | Lab 专属变化、关注对象和 Lab 判断 |
| /labs/{lab_id}/report | Lab 洞察报告和打印视图 |
| /labs/{lab_id}/settings | Lab 关注对象、成员和邀请设置 |
| /changes/{change_id} | 原文、作者、来源、链接和 Lab 判断 |
| /admin | 来源、Lab、成员、自动运行和雷达记录 |

文章详情支持 English、中文和 日本語。系统头像菜单支持页面语言和亮色 / 深色主题设置。

### 常用 API

~~~text
GET  /health
GET  /health/ready
GET  /docs

GET  /api/changes/today
GET  /api/changes/month
GET  /api/changes/{change_id}
GET  /api/documents/{document_id}
GET  /api/labs
GET  /api/labs/{lab_id}
GET  /api/labs/{lab_id}/changes/today
GET  /api/labs/{lab_id}/changes/week
GET  /api/labs/{lab_id}/changes/month
GET  /api/labs/{lab_id}/watch-items
GET  /api/translations/{change_id}?locale=zh|en|ja
~~~

完整接口以 FastAPI Swagger 为准：/docs。

## 数据库迁移与种子数据

迁移目录：services/api/migrations/versions/

执行迁移：

~~~bash
cd services/api
alembic upgrade head
~~~

初始化基础运行配置：

~~~bash
PYTHONPATH=. python -m app.db.seed
~~~

核心表包括：

~~~text
labs                  lab_profiles
sources               documents
analyses              entity_states
changes               lab_change_interpretations
watch_items           lab_watch_items
users                 lab_memberships
lab_invitations       lab_audit_logs
radar_runs            radar_settings
~~~

## 测试与质量检查

后端测试：

~~~bash
cd services/api
.venv/bin/pytest -q
~~~

前端类型检查：

~~~bash
cd apps/web
npm test
~~~

前端生产构建：

~~~bash
npm run build
~~~

Python 编译检查：

~~~bash
python -m compileall services/api/app
~~~

提交前建议额外运行：

~~~bash
git diff --check
~~~

持续集成配置位于 .github/workflows/ci.yml。

## 项目结构

~~~text
.
├── apps/web/                 # Next.js Web 应用
│   └── app/                  # Dashboard、My Lab、详情和管理页面
├── services/api/             # FastAPI 服务
│   ├── app/api/              # HTTP API 路由
│   ├── app/db/               # SQLAlchemy 模型和 seed
│   ├── app/services/         # 抓取、分析、AI、认证和雷达流程
│   ├── migrations/           # Alembic 迁移
│   └── tests/                # API 与服务测试
├── database/schema.sql       # 数据库结构参考
├── docs/                     # 产品、架构、Dify 和任务文档
├── docker-compose.yml        # PostgreSQL、Redis、MinIO、API、Web
├── .env.example              # 环境变量模板
├── LICENSE                   # MIT License
└── SECURITY.md               # 安全问题报告说明
~~~

## 生产部署建议

Docker Compose 适合本地开发和早期验证。部署到 AWS 等云环境时，可以拆分为：

- Web：ECS Fargate 或 App Runner
- API：ECS Fargate
- PostgreSQL：Amazon RDS for PostgreSQL
- Redis：ElastiCache for Redis
- 对象存储：Amazon S3
- 定时任务：EventBridge Scheduler、ECS Task 或 SQS Worker
- 密钥：AWS Secrets Manager 或 Systems Manager Parameter Store
- HTTPS：Application Load Balancer、ACM 和 Route 53
- 日志：CloudWatch Logs

生产部署至少应做到：

1. 使用托管 PostgreSQL，不把数据库作为长期运行的应用容器。
2. 使用密钥管理服务保存 OAuth、AI Provider 和数据库凭据。
3. 使用 HTTPS，并配置 Secure Cookie 和正确的 OAuth 回调地址。
4. 关闭 demo seed，不把真实 Lab 私有资料写入公共仓库。
5. 为抓取、AI 分析和失败任务配置超时、重试、限流和告警。
6. 将数据库迁移纳入发布流程，并设置备份和恢复演练。
7. 在正式暴露公网前完成权限、CSRF、密钥和依赖安全审查。

## 开源与安全

项目使用 MIT License。提交代码前请确认没有包含：

- API Key、OAuth Client Secret 或数据库密码
- .env、local.env、数据库文件和云平台凭据
- 下载的私有资料或未获授权的全文内容
- 真实用户信息和私有 Lab Profile

安全问题请按照 SECURITY.md 的说明私下报告，不要在公开 Issue 中发布凭据或可利用细节。隐私和数据处理说明见 PRIVACY.md。

## 当前边界

当前版本暂不包含：

- 用户上传资料、OCR 和 PDF 管理
- 多租户计费
- 完整的后台来源编辑器
- 专利数据的稳定多源 API 兜底
- 生产级任务队列和并发调度
- 完整的组织级权限、审计和合规流程

这些能力可以在数据源稳定、Lab 工作流验证和生产安全加固后继续建设。
