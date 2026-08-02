# Dispatcher 上游同步（REBASE）

- 上游仓库：Multica（地址待补充，许可证 NOASSERTION，商用/二次开发需法务确认）
- 基线版本：待首次 fork 时记录
- 本仓组织方式：直接复制 fork，改动集中在适配层与扩展层，不侵入核心调度路径

## 同步流程

1. 拉取上游新 tag，与本仓基线 diff
2. 只合入不影响 OGAS 改动的上游修复；冲突时以本仓四处改动为准：
   - liskin runtime 注册（仿 pi adapter）
   - 状态事件引出
   - ask 双向通道
   - API facade
3. 更新基线版本号与改动点清单

## 改动点清单

- [ ] liskin runtime 注册
- [ ] 状态事件引出
- [ ] ask 双向通道
- [ ] API facade
