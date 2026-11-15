# OpenClaw父进程死亡、恢复与原生new链路

2026-11-15，E128。产品固定E127 `500191a`，22模块未改；本次只增加可复现工具、三项回归和证据。最近真实部署/UI仍E123/e7d82cc，未操作服务或迁移绑定。

固定官方OpenClaw `41f2b981d240cab9e55b07cba991282a795317b5`、Node26.3.1，复用E126原构建，复核40份契约源文件及构建提交。运行真实Gateway、LocalRuntime、runtime_guard和官方`agent --local`，provider为仅回环的合成HTTP/SSE，投递为内存transport。没有真实账号、DWS、模型或UI调用。

## 实际进程与账本结果

1. 合成入站创建任务并进入running，完整UUID及session契约在官方工具开始前持久化。工具写下启动标记和PID后等待10秒，正常路径会写late文件。
2. 先核工具属于本次新建gateway后代树，再仅对该gateway发SIGKILL。其退出码为-9；lifetime pipe EOF触发guard的`gateway_pipe_closed`和原生SIGINT，日志为`sent_and_exited`。
3. 共捕获8个自有进程（gateway及7子进程），清理后全部退出；工具开始后12.0646秒未出现late文件。被中断任务没有validated-response或成功结果。
4. 两次重新打开gateway，任务保持interrupted/process_restart/result=null，无自动工具执行或额外provider请求。UUID、session契约、binding及原任务保留；只产生原ack和一条持久中断通知，第二次恢复没有重复通知。
5. 通过原生`/agent new`完成旧UUID及完整契约归档，generation由0到1，清除当前session而保留binding。随后一个新任务使用新UUID/工作目录；真实官方请求不含旧任务标记，完整返回的workspaceDir对应新generation。新任务完成并进入合成transport，旧interrupted任务全字段不变。

整段仅两个官方turn/两个provider请求，25检查全部通过。它补充父进程死亡和gateway控制链路，不重复E127六个直接适配器样本。原guard日志仍将脱组工具清理标为未独立验证；本次额外PID树核验只覆盖已捕获的7个子进程，不能外推任意后台服务、恶意脱组或系统故障。

## 三项冻结回归

[新增测试](../tests/test_openclaw_gateway_lifecycle.py)使用真实gateway/adapter/guard和合成CLI：

- 完成/重启续接/new/新代任务完整链路；旧任务与归档保持，文件摘要正确，丢失文件回执后沿原key/payload重试，不重跑生产工具。
- CLI exit0但stopReason=length时，已产生文件留存，任务failed；不排队结果文字或文件，也不重跑。
- gateway实际SIGKILL后，合成CLI原生中断回收自己的脱组工具；两次恢复不重做、不重复中断通知。

冻结源码Python3.14.6、E127同wheel的既有Python3.14.6及3.11.15安装各3方法通过。三份日志独立保留；22模块在工作树/冻结源/wheel/两安装逐字节相同，许可和六入口定义一致。没有新建wheel、重跑六入口help或旧423全量；不能写成426×3全量通过。冻结180份测试/工具/素材包含原177份不变、新增两文件，以及原来按后缀过滤漏计但一直在Git的UTF-8 CSV，不代表新增三个实现文件。

## 复现与证据边界

[执行工具](../scripts/probe_openclaw_gateway_crash.py)要求显式官方build目录、已冻结产品摘要和全新local输出目录；源码或产品不匹配会在CLI执行前拒绝。工具等待ready后再强杀自有gateway，保留前/后/最终账本、完整CLI输出、请求、进程树和检查结果。测试专用Node读取/启动钩子沿E126，只阻止已知环境访问；不是OS沙箱或任意生产binary的隔离保证。HOME未修改，未读取/复制既有runtime凭据。

```sh
python3 scripts/probe_openclaw_gateway_crash.py \
  --source-root local/openclaw-host-20261115/build-source \
  --product-freeze local/openclaw-gateway-lifecycle-20261115/freeze.json \
  --output-dir local/openclaw-gateway-lifecycle-new-run
```

这是人工复现入口，不是本轮下一步；已通过的样本不再重复。[脱敏证据](../evidence/2026-11-15/openclaw-gateway-lifecycle-validation.json)，原始材料仅`local/openclaw-gateway-lifecycle-20261115`。无产品失败或修复，开发首次3方法及冻结3×3均通过。

OpenClaw真实provider/UI仍未验，不复制Kimi/Codex/Pi凭据补验；四runtime全过不是原R09新增门槛。49/14/1及R01/R04/R06/R07/R12/R13/R14缺口保持，最终自检不勾选。下一独立项回到剩余MUST的新官方协议/UI入口；无新入口不重复旧实验、原观察或Qwen事务核验。
