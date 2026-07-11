# Codex 开发任务

## Sprint 0：工程可运行
1. 验证 docker compose build 与 up。
2. 修复所有构建错误。
3. 增加 API、PostgreSQL、Redis、MinIO 健康检查。
4. 增加前端基础测试与 API 测试。
5. 禁止硬编码生产密钥。

## Sprint 1：公共变化池
1. 实现 sources、changes、change_evidence API。
2. 实现公共变化列表和详情页。
3. 支持按重要性、时间、技术标签筛选。
4. 使用种子数据演示“旧状态→新状态”。

## Sprint 2：Lab 空间
1. 实现 labs、lab_profiles、lab_change_interpretations。
2. 同一公共变化生成不同 Lab 解释。
3. Lab 首页优先展示今日变化。
