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
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## 当前完成
- Docker Compose 基础设施
- Next.js 页面骨架
- FastAPI 健康接口与今日变化 Mock API
- 公共变化与 Lab 解释最小数据库模型
- 产品、架构和 Codex 任务文档

## 当前不包含
- 真实数据采集
- 大模型调用
- 登录权限
- 自动变化检测
