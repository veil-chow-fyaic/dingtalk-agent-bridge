# 续跑入口

```yaml
project:
  source_path: /Users/veil/Projects/dingtalk-agent-bridge
  plan_path: /Users/veil/Projects/dingtalk-agent-bridge/plans/completion
git:
  target_branch: codex/native-agent-channel
  core_branch: codex/complete-bridge
  remote_publish: user_requested_github_repository_update
  destination: https://github.com/veil-chow-fyaic/dingtalk-agent-bridge
  visibility: public_user_confirmed
  license: MIT
runtime:
  mode: 主Agent直接负责，子Agent隔离候选实现及离线验证
  checkpoint_minutes: 45
  single_agent: false
  chat_automation: deleted_do_not_recreate
goal:
  use_goal: false
```

用户已明确要求完成后续实现、测试、资料整理和GitHub仓库管理；取代旧交接停止、单Agent及不远程发布约定。当前接手入口为[HANDOFF](HANDOFF.md)，具体授权边界见[AGENTS](../../AGENTS.md)。复用当前checkout及分支，不另建产品或聊天；主Agent集成、提交、现场操作和仓库同步，子Agent在各自/tmp冻结源码实现及离线验证。

原bridge聊天自动化已经删除，不重建或以定时提示代替推进。业务观察是有界证据采集，与聊天调度分开。先读AGENTS、CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO及累计证据/账本；从可独立推进项实现到验证，不重跑没有新条件的失败路径。

GitHub目标、可见性及主代码许可需使用用户选定的值；已有GitHub更新授权无需再次逐步确认。发布前核当前树及将上传的历史，原身份、聊天、截图、日志、数据库、下载和凭据只留local。未达到所有MUST及最终自检时不创建稳定版完成声明。

现场仍限AIC测试群和原veil/liev私聊，正常受管业务许可保持；未知投递原key对账。认证、系统、共享bus及维护次序禁令沿用AGENTS，不因仓库整理扩大。
