# E039：运行器同组后代清理与真实私聊回归

2026-11-12。修复 LocalRuntime 返回后仍可能留下工具子进程的问题。原任务、授权、runtime 通用接口及验收等级保持。

## 故障与实现

隔离合成 provider 派生一个忽略 SIGTERM 的实际 OS 子进程。旧代码先 poll/wait 回收 CLI leader：leader 已退出时直接跳过清理；leader 收到 TERM 退出时又可能提前结束清理。两条复现均在 run 返回后释放子进程，观察到它仍写入 late-artifact。初次过短 timeout 的准备失败也保留在本机日志。

现在先保留未回收 leader 的 PID，向其所属组发 TERM、观察退出、向同组发 KILL，最后回收 leader。Codex 的最终文件等待同样不提前回收。组信号被拒绝时仅向已持有的精确子 PID 发信号；不通过 Popen.terminate/kill 隐式 poll。第一次修复的 ChildProcessError 失败保留，未算通过。

macOS 的 os.waitid 从 Python 3.13 才提供。旧版使用 POSIX ps 观察尚未回收的直属子进程是否为 zombie，仍不提前释放 PID；本机 Python 3.12 的17项真实进程测试通过。Python3.11/Linux未实机认证，不扩大环境通过范围。[Python官方契约](https://docs.python.org/3/library/os.html#os.waitid)

此机制只清理未主动脱离所属进程组的后代，不是 OS 沙箱，也不承诺控制自行 setsid 的进程。没有修改 DWS 或传输实现。

## 用户视角验证

两个空闲 gateway 加载初始修复后，veil 在原生钉钉与 liev 私聊中发送一次 DAB-RUNTIME-CLEANUP-20261112-001：实际用 Python 计算419乘23，写文件并回传。Kimi 的 Bash 确实执行乘法与 write_text，工具返回9637。liev 完整回复“419 × 23 = 9637”可见；文件卡片经原生保存框下载，再从 Finder Quick Look 打开，全文为 `419 * 23 = 9637`。

客户端下载件16B，SHA-256 `6fe4a2c08ebad156d1b01e33d8f18adbc53f9a9a51f223407f889d8e73656bfc`；与 exports、outbox 暂存和官方资源回读完全相同。一个新任务、三条确认回复；native session、全部旧任务/投递/事件/日志保持，无自回声任务，群无变化。DM48任务/121outbox（120确认1旧拒绝）/130传输/179事件；群3/7/12/76。

后来补充的 Python<3.13 兼容分支另经本机3.12进程测试、新wheel与空闲重载验证；上述UI在兼容补丁之前完成，不重复发送任务冒充新证据。当前3.14仍走 waitid 分支。两次维护均只重载gateway，传输与原观察未重启；最终 live doctor 通过。

## 验证结果和未解决失败

- 初始修复全量160项通过；新增4项覆盖 leader提前退出、忽略TERM后代、取消且不影响无关进程、合成Codex完成事件。
- 最终兼容补丁全量160项有2个错误，均为既有 service_manager during-shutdown 身份保护分支；运行器测试无失败。不是“最终160全绿”。
- 两个失败测试随后仅做一轮带ps捕获的限定诊断：6次执行/187观察未复现。该结果不能消除之前两次失败，E027根因仍未知；没有放松身份保护或强杀。
- 最终干净wheel、新venv六入口、18模块摘要一致通过；33项现场只读审计与2个负向注入通过。
- 原观察1107样本、9.225h、6不可达；既有3poll_error和维护保留。未满24h，不能标项目完成。

共享证据为 runtime-group-install.json、runtime-cleanup-validation.json、runtime-cleanup-ui-ledger.json、runtime-cleanup-audit-negative.json。私有复现/失败日志、UI、原件、账号和状态均在local/runtime-orphan-20261112，不入Git。

```bash
python3 scripts/accept_runtime_cleanup_ui.py
python3 -m unittest discover -s tests -p test_agent_runtime_process.py
```

下一段先为 manager 的身份保护错误补本地诊断记录（expected/current/原始ps状态），不改变判定或信号权限；有失败现场再定位。没有新证据不盲目重跑生命周期。原生语音/普通多附件、入站引用、原群范围、失效refresh及24h缺口继续保留。
