# 续跑入口

```yaml
project:
  source_path: /Users/veil/Projects/dingtalk-agent-bridge
  plan_path: /Users/veil/Projects/dingtalk-agent-bridge/plans/completion
git:
  target_branch: codex/complete-bridge
  remote_publish: false
runtime:
  mode: 完整实现与验收
  checkpoint_minutes: 45
  single_agent: true
goal:
  use_goal: false
```

用户已要求安排长过程闭环，E114复用原heartbeat bridge并恢复ACTIVE，每30分钟在本聊天续作。不是新实现/新线程，不增加独立目标系统。沿已有计划执行；先读AGENTS、CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER、99-执行偏差日志，然后09里程碑/10自检。

每次取关键路径最前可做项，实际实现、验证、修复，按改动需要与当前授权部署/真实UI，留证并本地提交。完成一段继续，不只巡检或重新规划。阶段状态/失败写回文件；上下文重置从这些文件续接，不从旧聊天猜状态。

只准AIC测试群和原veil/liev私聊，企业大群/旧群禁止。真人账号与通用runtime方向不变；不索取密码/第二账号，认证和系统操作禁令见AGENTS。原key未知投递先核对，不换key或UI补发。Mac/Codex离线无法执行，心跳不构成开机自启服务或24h健康证明。

E132补充：阶段报告按历史时点解释，现状只在总览及活动清单维护。受阻路径无新证据不重试；全部剩余依赖外部条件时保持未完成，不制造巡检。文档索引及历史正文检查见 `scripts/review_documentation.py`。
