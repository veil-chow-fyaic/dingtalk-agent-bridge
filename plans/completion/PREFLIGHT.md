# 续作前置核对

E135接手先读[HANDOFF](HANDOFF.md)：本会话已按用户要求交接，心跳已PAUSED，不自动恢复。下列为未来接手步骤，不在交接时启动新实验。

1. 读[AGENTS](../../AGENTS.md)、INIT、CURRENT_MISSION、MODE、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER及99-执行偏差日志；核原checkout、codex/complete-bridge、未提交改动归属，不从聊天空目录另做实现。
2. 从[总览](../../docs/102-user-requirements-and-roadmap.md)区分现场2467fe2/E134（E133组合实现、包含500191a OpenClaw代码但未绑定/真实模型验收）、最近UI E131和E132文档治理。已有冻结测试不与当前HEAD混比，无代码变化不重跑全量。
3. 选择未完成且有明确可用入口的项，先读对应证据及loop guard。E131模型403需既有服务访问恢复证据；DWS ready不解除这个条件。旧UI路径和两份旧观察不重复。
4. 只为下一动作读取必要现场状态，文档工作不制造DWS/模型/UI探针。经理进程running、HTTP健康、released或last_sync.at都不能替代真实覆盖/交付。
5. 精确会话、显式profile与白名单沿既有授权；仅AIC及原私聊，企业大群/旧群禁测。未知原key对账；维护用原manager实际归属，runtime迁移需原生new/零未决/显式binding。
6. 用户已登录成功的历史保留，不索取密码/第二账号；禁止auth/doctor/Keychain及自动认证修复等AGENTS动作。凭据故障保持暂停，不能以正常恢复授权绕过。
7. 提交前更新文档索引、review_documentation、review_acceptance、verify_handoff写manifest并核对、verify_privacy扫暂存blob、git diff --check。原始身份/聊天/截图/日志/下载只留local。

全部MUST和最终自检尚未满足时，coverage返回未完整是正确结果，不修改判据让检查变绿。
