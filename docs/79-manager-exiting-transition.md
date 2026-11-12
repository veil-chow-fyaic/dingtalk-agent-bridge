# 等待已发TERM进程的退出过渡

2026-11-12，E062。E061第一次保存到实际失败的同次ps：已合法发送TERM的原进程仍保留启动时间，状态为?Es，完整命令消失为(python3.11)。本机系统man ps对E的说明是“The process is trying to exit.”；过去代码把这个中间状态立即当作身份变化并报错。

现在仅在已发TERM的等待阶段，要求同次ps成功、PID与启动时间相同、附加状态包含E，才继续原时限内的只读等待。它不是身份授权，不发第二个信号，也不把E本身当stopped；必须后续观察确认消失。其他状态的命令变化、启动时间变化、发信号前身份变化仍拒绝；持续E到超时仍报告未完成，不强杀。

## 验证与边界

- 两项新回归覆盖E→消失、两个发信号前位置、不同启动时间E、非E命令变化、持续E超时。旧源码/旧已安装wheel各2失败，修复后通过。
- 将E061保存的精确原始观察输入旧/新manager，ps与kill均替身，避免触达已结束PID。旧版第3次观察拒绝，新版第4次观察到消失后完成，二者均只调用1次TERM；这是捕获证据回放，不是新现场强杀。
- 源码和新wheel在Python3.14/最低3.11各197项通过，包含真实合成进程manager运行/停止和E061的两项进程死亡恢复测试。新venv六入口/19模块与冻结源码、wheel一致。测试均经清理前诊断入口。
- 初次3.14安装测试前置检查不允许任何local目录，因前一3.11运行已生成合成test-evidence而拒绝，尚未执行测试。保留原日志后，仅允许该单一诊断子目录，其余账号路径仍不存在；随后3.14完整通过。

唯一产品变化是service_manager.py。它由命令按次执行，当前status已使用新源码；传输/gateway模块不变，三个服务PID、配置/两路旧记录/session/执行日志保持，无需为此重启服务。26项审计通过，原观察同PID/起点、约13.421h、7不可达，24h仍未满。

E061原失败、E059诊断丢失和E039历史错误全部保留。本修复定位并覆盖的是已捕获的退出过渡，不能声称所有过去未观察的错误均为此因。没有新钉钉消息、原生UI、凭据故障或授权变化。

```bash
python3 scripts/run_tests_with_evidence.py
PYTHONPATH=. python3 scripts/accept_manager_exit_transition.py
```

[26项核验](../evidence/2026-11-12/manager-exit-transition-validation.json)、[冻结安装](../evidence/2026-11-12/manager-exit-install.json)。原始ps/手册/回放与日志在local/manager-exit-20261112和E061私有目录，不入Git。
