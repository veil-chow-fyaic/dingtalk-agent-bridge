# Codex参数核验与一次新本地任务

2026-11-13，E105。[结构化记录](../evidence/2026-11-13/codex-cli-timeout-diagnostic.json)。E104已提交c5ee1fe；本次产品/配置/服务未变，不重复331项。不是新UI通过证据。

本机官方Codex CLI 0.164.0。仅`--version`、exec/resume帮助和当前适配器完整参数加`--help`四类解析核验均exit0，未启动模型。已实际检索并读取[官方exec文档](https://learn.chatgpt.com/docs/developer-commands#codex-exec)，本机帮助进一步确认两个子命令都支持ignore-user-config、output-schema、JSON和最终消息文件参数；ignore-user-config忽略用户配置但仍使用原CODEX_HOME认证。没有改HOME、读/复制凭据或重新登录。

随后只有一次新的独立本地任务：实际Python计算31×43并写合成JSON，限制60秒、禁止网络工具/DWS/外部沟通/工作区外访问。任务不是旧聊天的重做，也没有触发钉钉投递。结果为timeout（60.110秒）：thread.started、turn.started后出现顶层error“Reconnecting... 2/5 (request timed out)”，没有工具item、turn.completed或输出文件；宿主守护记录cleanup_complete=true。宿主只启动一次，CLI内部出现重连，不能称完全没有重试。

初次11月11日失败日志摘要保持不变。当前进程环境仅记录变量是否存在，不记录值，不把此时环境外推为旧任务环境。CEO固定源码的safe environment/代理保留规则作为线索；本项目继承父环境，不能照搬它的环境丢失病因。

新证据排除了这次调用的参数解析失败，并复现了有界请求超时；没有401/权限拒绝或工具执行证据，也不足以确定代理、网络、服务端或配置哪层造成超时。**不宣称Codex已接通、认证已坏或根因已解决。** 不扩大超时、不重复同任务、不中途切模型/凭据；下一次必须有新的可验证环境/服务证据或修复依据，再做新受控任务及IM UI闭环。Kimi仍满足至少一个本地执行器的MUST门槛。
