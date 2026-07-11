# Research Radar

面向技术研究所的 Lab 级科研变化雷达。

## 启动

```bash
cp .env.example .env
docker compose up --build
```

访问：
- Web: http://localhost:3000
- API: http://localhost:8000/health
- API Readiness: http://localhost:8000/health/ready
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## 本地检查

```bash
python -m compileall services/api/app
pytest services/api/tests
cd apps/web && npm test && npm run build
```

## 数据库

API 容器启动时会自动执行：

```bash
alembic upgrade head
python -m app.db.seed
```

核心接口：
- `GET /api/changes/today`
- `GET /api/labs`
- `GET /api/labs/{lab_id}/changes/today`
- `GET /api/changes/{change_id}`

## 当前完成
- Docker Compose 基础设施
- Next.js 页面接入真实 API
- FastAPI 健康接口、依赖就绪检查与数据库驱动的今日变化 API
- Alembic 迁移、初始化种子数据、公共变化与 Lab 解释最小数据库模型
- 产品、架构和 Codex 任务文档

## 当前不包含
- 真实数据采集
- 大模型调用
- 登录权限
- 自动变化检测
