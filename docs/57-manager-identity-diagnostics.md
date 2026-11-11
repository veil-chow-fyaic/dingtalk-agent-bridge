# E040：manager 身份保护错误的私有诊断

2026-11-12。E039最终全量回归曾出现两次 during-shutdown 身份保护错误，不能用随后重跑通过消除。本轮补齐故障证据能力，未宣称修复该历史根因。

`process_identity`可将同一次ps的原始stdout、stderr、退出码、时间与解析身份写入内存观察。启动/关闭因身份不匹配而拒绝时，manager把expected、该次observed、阶段与组件追加到本地`local/runtime/manager-identity-errors.ndjson`，权限0600。不会为了诊断重新ps而错过瞬间状态；status仍只读，不写错误文件。记录可能含私有路径/命令，不能进入Git或共享报告。

不修改原身份判据、PID复用保护或信号范围；诊断写入失败也继续拒绝。两项新测试验证：TERM后不匹配恰好留下第三次观察且不多发信号；诊断文件不可写也不放行信号。原foreign进程、pre-signal竞态等测试保持。

## 验证与明确限度

- manager 15项通过；Python3.14.6与本机Python3.12.13全量各162项通过。
- 完整测试的预期foreign进程场景捕获过`ps`只呈现括号内进程名的过渡状态；该进程不是被关闭的原进程，不能据此认定历史根因。
- 随后仅对合成直属子进程做一次上限64次的“TERM后立即观察”实验，64次均正常停止，未复现原错误。达到本路径限制后停止，不继续刷循环或把无复现改为已修复。
- 干净wheel、新venv六入口/18模块摘要通过；manager是按次执行CLI，新代码在下次调用生效，无需重启现网。
- 现场三个PID、两路任务/会话/outbox/传输/事件/运行日志不变，无新IM消息。原观察1128样本9.4h、6不可达；旧3poll_error及维护保持，24h未完成。

共享证据：manager-identity-install.json、manager-identity-diagnostic-validation.json。原始ps、完整测试日志及合成实验在local/manager-identity-diagnostic-20261112。

下一次若发生保护错误，先只读复核该私有日志和实际状态，不换PID、不强杀、不放松检查。现无新失败证据，转做独立附件元数据与Unicode CSV真实UI边界；不重放旧群/引用/文件实验。
