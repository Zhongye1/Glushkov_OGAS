# Arkhiv 上游同步（REBASE）

- 上游仓库：EagleRAG（地址待补充，Python 项目，MCP Server + Milvus）
- 基线版本：待首次 fork 时记录
- 本仓组织方式：直接复制 fork，底层检索引擎（ingest/query/retrieve）不动

## 同步流程

1. 拉取上游新 tag，与本仓基线 diff
2. 只合入不影响 OGAS 改动的上游修复；冲突时以本仓改动为准：
   - workspace 级权限封装（plugin_namespace 之上）
   - 结构化命名空间（PRD / 接口契约 / UI 规范 / 历史决策）
3. 更新基线版本号与改动点清单

## 改动点清单

- [ ] workspace 权限封装
- [ ] 结构化命名空间
