# E042：真实工具运行中停止私聊gateway与恢复

2026-11-12。veil从原生钉钉私聊提交一次前台Python等待任务：写开始标记JSON、等待90秒、再写TXT回传。私有watcher确认新任务处于running，并读取实际Python→Bash→Kimi→私聊gateway的PPID链；manager记录与现场进程身份完全相符后，才对该gateway执行正常stop。没有从任务提供的PID直接发信号，也没有停止传输、群gateway或原24h观察器。

实际Bash命令包含写开始标记、time.sleep(90)和随后写TXT。Python/Shell属于另一个进程组，但Kimi正常退出时也退出了；停止后的现场查询确认四个原进程均已消失。这个结果只覆盖本次正常SIGTERM关闭链，不能据此外推恶意脱离进程、SIGKILL恢复或OS级沙箱。首次取消运行的events.jsonl只有版本元事件，未输出完整工具结果；实际执行证据来自独有开始文件、同次ps命令与父子归属，不虚构完整工具日志。

原任务变为cancelled/RuntimeStopped，无产物。正常start复用传输与群gateway，只替换私聊gateway；同一outbox key的取消反馈确认一次。veil客户端中实际看到liev的“[Agent] 任务已停止。”及“通过AI发送”标识。开始后104.38秒检查：开始标记保持，原计划的延迟TXT不存在。

随后veil再从同一私聊提交一次只读任务：实际Python检查两文件、读取marker并计算37×19。Bash返回started_exists=true、late_exists=false、原marker和703；最终完整短回复在原生客户端可见，没有文件回传。新任务completed，同一native session，原任务没有再次执行。

| 核验 | 结果 |
|---|---|
| 本次新增任务/投递 | 2任务：1 cancelled、1 completed；4条文字outbox全部确认，无文件与自回声 |
| 完整账本 | DM52任务/131outbox（130确认、1旧拒绝）/140传输/193事件；群3/7/12/76不变 |
| 历史与进程 | 旧任务/outbox/传输/事件及日志字节保持；仅私聊gateway正常替换，传输和群归属保持 |
| 只读审计 | accept_active_gateway_stop_ui.py 41项通过；内存负向4项拒绝晚写、未满等待、残留工具、错误父进程 |
| 健康/观察 | live doctor通过；原观察1175样本、9.792h、6不可达，原3poll_error及维护保留，未满24h |

产品代码沿用E041，没有为本实验修改停止策略、身份检查、运行器或DWS。旧E027/E039 manager during-shutdown错误仍未定位；本次成功不是其已修复证明。共享evidence/2026-11-12/active-gateway-stop-ui-ledger.json与active-gateway-stop-audit-negative.json；原始UI、命令/父子链、账本、两次唯一发送记录与维护窗口在local/active-stop-ui-20261112。

已确认实验只读复核，不重新发送相同任务。群新增范围、入站引用、原生语音/独立video、普通单消息多附件、真实失效refresh及24h仍按矩阵保留；下一独立项核清官方会议/钉盘工具在现有授权中的可用边界，优先只读，不扩权限或触达第三人。
