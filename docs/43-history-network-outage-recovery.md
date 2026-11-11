# 私聊历史接口真实断网与任务补收

2026-11-12，E023。对私聊DWS子进程的HTTP请求制造78.310秒网络故障；veil在故障期间通过原生钉钉UI发送一次合成计算任务。恢复网络后，无需重发或重启服务，bridge自动补收，Kimi实际运行Python计算37×43，liev回传确认、文字结果和36字节文件。文件在钉钉客户端下载，并在Finder Quick Look打开，内容1591与生成件字节一致。

## 故障机制和官方边界

固定官方v1.0.67源码 `internal/transport/client.go` 使用 `http.ProxyFromEnvironment`，同目录 `proxy_env_test.go`覆盖代理环境行为。本次临时私有launcher保留官方二进制和全部命令参数，只对私聊路由的子进程设置HTTP(S)代理到一个已绑定、未监听的本机端口。套接字随exec保留，不是伪造CLI输出，也没有更改整机代理、撤销凭据或修改账号权限。

只读预检实际得到官方退出1、`io_timeout`、`proxyconnect tcp ... i/o timeout`。故障窗口内官方日志记录5次 `chat/list_individual_chat_message` 超时，传输health显示私聊 `BridgeError`。群的历史同步继续推进，群任务/消息/投递无变化。既有Stream连接和原生客户端没有被断网；因此结论限定为私聊历史HTTP路径恢复，不能外推整机断网、Stream socket分区或真实授权过期恢复。

launcher只有180秒有效窗口，本次在78.310秒主动移除故障标记。测试前的manager停启是部署装置，测试后的停启是撤除装置；两者都记入维护日志。故障到任务完成之间三个受管PID与启动时间不变，恢复无需进程重启。

## 实际证据链

| 阶段 | 观察结果 |
|---|---|
| 故障生效 | 官方历史请求真实超时，私聊health报错；群同步正常 |
| veil发任务 | 原生UI点击发送一次，合成任务在本人侧可见 |
| 断网期间对账 | 独立未加代理的官方只读调用已看到该messageId；bridge私聊事件、游标、任务、投递和运行文件仍与故障前相同 |
| 解除故障 | 不重发，history恢复并收取同一messageId，仅产生一个任务 |
| 实际执行 | Kimi日志只有一次Bash工具，执行Python `result = 37 * 43`，工具输出1591；无办公调用 |
| 用户收到结果 | UI看到liev“已接收任务”和文件卡片；从钉钉保存文件，Quick Look显示两行计算结果 |
| 重复与历史检查 | 仅新增一个完成任务、三条确认outbox/传输投递；回复不触发回声任务，旧任务/失败/日志保留，清理后无新增重复 |
| 撤除装置 | 服务配置恢复测试前精确字节，DM办公上下文恢复原官方binary；固定二进制摘要不变，故障标记不存在，manager和live doctor通过 |

短文字“网络恢复验收：1591”有历史回读，但未单独观察对应聊天视口，不列为该气泡UI通过。文件内容有真实下载打开证据。原始账号、参数、日志、完整AX、截图只保留在 `local/network-recovery-20261112/`。

只读复核：

```bash
python3 scripts/accept_history_network_recovery.py
python3 scripts/accept_long_bubble_ui.py
```

42项网络恢复检查通过；内存注入“断网游标已变化”“缺官方失败证据”“下载文件损坏”三项均被拒绝，不改原始现场证据。E021办公69项、E020管理器39项只读复核仍通过。此次没有修改产品运行代码，沿用E021最终126项回归/干净安装版本，不将审计条数当新增单元测试。共享结果见[现场审计](../evidence/2026-11-12/history-network-recovery-ledger.json)、[负向验证](../evidence/2026-11-12/history-network-audit-validation.json)。

24h观察器保留原run/PID/19:36:08起点；冻结检查点669样本、5.57小时、累计4个不可用样本（本轮清理维护新增1），没有重置成零失败。该计数是采样可达性，不等同全程零中断或所有路由健康。最早11月12日19:36后评估真实24h；授权过期与完整Stream断网仍待独立证据。

## 后续Stream隔离只读检查

01:20后官方 `event status --profile … --format json` 成功读到一个personal bus、两个订阅和两个consumer。逐个核对consumer父PID，两个均属于当前bridge传输进程。固定源码的Identity.Key按账号/client/source生成，不含会话；Discover先连接既有IPC，只有连接失败才spawn。因此两个会话复用同一个上游bus，不能把新consumer的代理环境当成旧WebSocket已经断网。

本次状态是 `idle`、来源 `inferred`。源码把60秒无新事件后的连接标为空闲，这是推断而非新的实收/连接探针。`DWS_CONFIG_DIR`改变整个配置命名空间，不是已验证的仅event隔离开关；没有为此复制凭据、改profile或停止daemon。共享证据见[隔离与官方路线补查](../evidence/2026-11-12/stream-isolation-and-official-route-review.json)。下一步需验证SDK WebSocket的代理路径与daemon仅有本项目consumer的条件，再设计有界断连/恢复；不将这次只读检查计为网络验收通过。
