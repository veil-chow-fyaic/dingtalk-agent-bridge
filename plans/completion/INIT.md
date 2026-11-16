# 续跑入口

```yaml
project:
  source_path: /Users/veil/Projects/dingtalk-agent-bridge
  plan_path: /Users/veil/Projects/dingtalk-agent-bridge/plans/completion
git:
  target_branch: codex/complete-bridge
  remote_publish: false
runtime:
  mode: 单Agent手动续作，心跳不自动恢复
  checkpoint_minutes: 45
  single_agent: true
goal:
  use_goal: false
```

E135用户要求整体检查后交接，当前以[HANDOFF](HANDOFF.md)为接手入口。实查原heartbeat bridge已PAUSED，未更改调度，不自动恢复；E114的ACTIVE是历史配置。不是新实现/新线程，不增加独立目标系统。用户明确接手后沿已有计划执行；先读AGENTS、CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER、99-执行偏差日志，然后09里程碑/10自检。

每次取关键路径最前可做项，实际实现、验证、修复，按改动需要与当前授权部署/真实UI，留证并本地提交。完成一段继续，不只巡检或重新规划。阶段状态/失败写回文件；上下文重置从这些文件续接，不从旧聊天猜状态。

只准AIC测试群和原veil/liev私聊，企业大群/旧群禁止。真人账号与通用runtime方向不变；不索取密码/第二账号，认证和系统操作禁令见AGENTS。原key未知投递先核对，不换key或UI补发。Mac/Codex离线无法执行，心跳不构成开机自启服务或24h健康证明。

E132补充：阶段报告按历史时点解释，现状只在总览及活动清单维护。受阻路径无新证据不重试；全部剩余依赖外部条件时保持未完成，不制造巡检。文档索引及历史正文检查见 `scripts/review_documentation.py`。

E133用户明确纠正主线：IM通道独立于可选runtime，Kimi订阅拒绝只阻塞绑定它的模型任务。E134已部署组合并验两路API/官方下载原件，仍按通道字节/API/真实UI分层验收，不把离线代码通过换算成R07通过。

E136接手更新：本轮从用户给出的HANDOFF继续独立截止采集工具，冻结观察专项30×2通过，未改产品/部署/调度或启动真实观察；加载版本证据仍缺，现行动作见TODO。E135交接停止仅描述上轮会话。
