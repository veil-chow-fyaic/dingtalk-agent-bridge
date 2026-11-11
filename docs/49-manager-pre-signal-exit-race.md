# 停机前自然退出竞态修复

2026-11-12，E030。管理器在两次身份检查之间遇到原进程自然退出时，原代码把 `process_identity() is None` 与“PID已被另一活进程占用”一起判为身份变化。现在前者返回已停止，不再发送信号；后者仍拒绝，未放宽PID归属保护。

## 可复现证据

新增真实隔离子进程回归：启动一个合成transport，在第一遍存活检查后、第二遍发信号前的身份读取时，让已拥有的子进程退出并wait回收。旧实现实际抛出 `PID ownership changed at shutdown`，日志保留；修复后该测试通过，进程确已停止。

另一新增回归令第二遍身份变成不同活进程，仍抛出原错误且 `os.kill` 未被调用。已有真实外部进程保护、逆序停止、失败回滚、配置漂移和进程启动器切换等用例保持。13项管理器测试和139项全量回归通过；不对已通过的同版全量重复跑测来增加数量。

本修复只处理 **发信号前进程已退出**。E027现场报的是 **发信号后during-shutdown身份变化**，没有新证据证明两者同根，不宣布E027根因已解决；原两轮未复现记录继续保留。没有重复重启现场来追逐偶发错误。

## 安装及现场影响

从已跟踪文件导出无local账号数据的干净源码，独立venv构建wheel并安装，六入口help正常，18个模块的源码/wheel/安装目录摘要一致。只有service_manager模块变更，传输和gateway代码不改；当前管理器是按次运行的CLI，下一次调用直接加载新代码，三个常驻进程保持原PID，没有部署维护中断或新聊天。

现场status显示三进程健康；与E029冻结快照比较，双路jobs/outbox/meta/deliveries/events/运行日志逐项不变。原24h观察继续，尚未满时长。

复核：`python3 -m unittest discover -s tests -p test_service_manager.py`。共享证据见 `evidence/2026-11-12/manager-exit-race-validation.json`、`manager-exit-race-install.json`；原始失败/成功日志、新venv和wheel仅在 `local/manager-exit-race-20261112/`。
