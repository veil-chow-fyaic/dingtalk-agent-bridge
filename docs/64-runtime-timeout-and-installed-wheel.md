# E047：真实执行超时、用户反馈与最低Python版本

2026-11-12。补齐真实私聊执行器超时路径：准确说明时限和结果不确定性，实际工具清理、无迟到写入，原 gateway 不重启即可执行下一任务。新增提示不改变任务状态、回传协议、幂等键或 runtime 选择。

## 变化与回归

此前运行器达到 deadline 时只发通用“本次任务未完成”。现在针对 RuntimeStopped(timeout) 告知实际配置秒数、未完成/未自动重做/未发送结果文件，并说明已经产生的文件或外部变更可能仍存在，建议先核对再拆分任务。取消和其他失败提示保持原义；不承诺回滚已经完成的副作用。

新增回归先在旧实现失败，修复后确认超时为 failed/RuntimeStopped/result=null、局部文件留本地、无文件交付；重启不重做且下一任务可执行。Python 3.14 全量165项、Python 3.12 gateway35项通过；干净新 wheel 六入口/19模块摘要相同，无账号数据。

同时验证 pyproject 声明的最低版本 Python 3.11.15。新 venv 离线安装该 wheel，把 tests/scripts/fixtures复制到单独目录，明确不包含 dingtalk_bridge 源码包、local 或账号数据，并清除继承的 PYTHONPATH。主进程实际从 site-packages 导入，测试子进程的显式源码搜索目录也没有源码包，因此同样使用已安装包。完整165项通过（35.445秒），包含真实子进程和本机HTTP验证；不是只运行入口 --help。未安装或升级用户全局Python。

## 原生私聊闭环

两路gateway空闲时加载提示修复；私聊配置仅暂将 timeoutSeconds 从600改成90，原文本摘要保留，身份/profile/授权不变。veil从钉钉私聊发送一次 DAB-TIMEOUT-20261112-047；Kimi实际Python写started标记，sleep(150)，之后才应写late文件。

只读观察核对 Python→Shell→Kimi→runtime_guard→gateway 五进程父子链。运行日志创建后90.399秒任务成为 failed/RuntimeStopped，无结果；同组工具和守护退出，gateway身份/manager记录保持，控制器没有发送任何进程信号。该期限包含模型启动/推理，因此Python本身运行约69.84秒，并非让Python完整跑90秒。

liev完整超时提示已在veil原生窗口目视确认。工具开始后155.203秒再次检查，超过150秒等待和155秒护栏，started保持、late不存在。veil发送一个新的明确只读任务；同一gateway、native session下，Kimi真实Python读取两文件状态并计算19*37，结果703。liev完整回复marker、started存在、late不存在和703，原生UI可见。没有回传文件，没有重做原失败。

随后在空闲时恢复私聊配置原始600秒，整份配置SHA与实验前精确一致，再正常重载私聊gateway。该维护发生在后续任务成功之后，不把重启后的恢复冒充同进程恢复。群gateway和transport在这次恢复时保持。原24h观察器未重置。

## 审计与剩余边界

- `scripts/accept_runtime_timeout_ui.py`：42只读检查；5负向拒绝错误父子链、人工清理、过早观察、偷偷重启gateway以及未精确恢复配置。runtime-timeout-ui-ledger/audit-negative.json。
- runtime-timeout-validation/install.json：测试版本、日志摘要、wheel摘要、精确时长、doctor通过。私密配置/身份、原始工具/进程日志、AX与截图仅在 local/runtime-timeout-ui-20261112。
- DM61任务/151outbox（150确认1旧拒绝）/160传输/222事件；新增两任务四文字确认。群3/7/12/76与所有旧记录/日志/session保持。当前传输25113、群gateway53263、私聊gateway56141仅为快照，操作前重新核对。
- 原观察1315样本约10.960小时，6不可达、3poll_error和维护保持；未满24h。历史manager关闭身份错误未消除。本次不是OS沙箱、守护被强杀或外部副作用回滚验证。

本轮C01先按已有官方契约及公开入口复核，无新普通文件组合、Mac引用或原生语音入口，未发送试探消息、未重复旧菜单。原矩阵阻塞不改绿。后续继续有明确新入口的私聊场景和最终交接检查；群新实验仍需第三人范围答复，真实失效refresh与完整24h保留原门槛。
