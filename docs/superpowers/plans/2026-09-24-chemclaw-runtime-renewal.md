# ChemClaw 运行内核整改实施记录

规格：[已批准设计](../specs/2026-09-24-chemclaw-runtime-renewal-design.md)。比较基线：本地 75c1373，上游 cc2b921b187a5333df479ca27f211e0bb2631d68。

- [x] 阶段一：计量与诊断、模型能力设置、完整请求预算、摘要质量与回读、防重复压缩；定向回归并提交。
- [ ] 阶段二：通用执行与工具发现、业务 Skill、Channel 等价权限；定向回归并提交。
- [ ] 阶段三：分段检查点、预算续跑、断流恢复、截断终态；定向回归并提交。
- [ ] 阶段四：离线长任务回放、前后端组合验证、构建标识、文档及最终提交。

## 已知基线

整改前五文件回归 124 passed；真实日志 16 次摘要 BadRequestError，最近故障会话 8 次降级精简及 2 次断流。既有配置 95%/1M，未知模型窗口回退 128k。追踪器用量字段错配已离线复现。

## 实际验证

实施中逐阶段补充。安装版及真实 Provider/Channel 验收不计作离线测试通过。

阶段一：99 passed（runtime_budget/compaction/compaction_engine/model_errors/provider_router），GUI tsc --noEmit 通过，git diff --check 通过。增加模型能力设置界面与端点隔离配置。真实网关错误仍待新版运行日志确认。
