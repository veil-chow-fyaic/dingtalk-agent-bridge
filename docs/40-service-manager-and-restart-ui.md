# 统一后台管理与重启后真实任务验收

2026-11-11。新增 `dab-service`，统一管理一个本机传输服务和显式选择的多个 gateway。现有群/私聊两个 gateway 已迁入，原账号绑定、账本、游标和 Kimi 会话沿用。管理器属于普通账号 bridge 的本地运行补充；身份、聊天、历史、文件与办公接口仍复用 DWS，没有替代官方鉴权或新增 bot。

11月12日后续：[E021](41-official-office-agent-ui.md)已经该管理器维护部署官方工具上下文。本文119测试/17模块属于E020冻结版本，最新为126测试/18模块；历史审计核对原wheel、原导出与原部署摘要，当前源码不同另行报告，不要求旧wheel等于后来升级的源码。未重写E020原始验收记录。

## 配置与运行

按[安装说明](35-install-and-doctor.md)安装，包现在有六个入口。复制公共 `config.routes.example.json`、`config.agent.example.json` 到自己工作目录的 `local/`，填经过官方发现及实际消息核对的 profile、会话和发送人标识；不要复制本项目的账号状态。每个 gateway 的 `bridgeConfig` 必须指向同一份服务配置，`accountId`/`conversationId` 必须匹配所选路由，同一会话只能有一个 gateway。身份发现、精确选择和旧账本迁移见[配置操作](23-continuation-and-migration.md)。配置完成后先只读核验：

```bash
.venv/bin/dab-doctor --agent-config local/agent-config.json
.venv/bin/dab-service --agent-config local/agent-config.json plan
```

`plan` 不创建状态、不调用 DWS、不启动服务。默认只管理传输，执行器必须显式选入：

```bash
# 通用 IM 工具，不启动任何 Agent runtime
.venv/bin/dab-service start
.venv/bin/dab-service status
.venv/bin/dab-service stop

# 选入已配置并授权的 gateway；启动后会实际处理任务并回复
.venv/bin/dab-service --agent-config local/agent-config.json start
```

可重复 `--agent-config` 选择多个不同会话。`--root` 指定工作目录；默认当前目录。当前端口为 127.0.0.1:18768，与现有 gateway/consumer 一致。安装包只依赖 Python 标准库，生命周期锁需要 POSIX；本轮实机为 macOS arm64、Python 3.14.6，其他环境尚未现场验收。

重复 `start` 要传相同且顺序相同的配置列表，进程仍存活时复用原 PID；改变活跃配置或删减 gateway 必须先显式 `stop`。配置文件被移走时，`stop` 仍可按保存的进程归属停止。`status` 只报告归属和存活，`ok: true` 不是模型可调用或健康证明；`all_running` 才表示记录中的进程全部存活。另用 `dab-doctor --live` 检查传输健康，再以真实任务验证 runtime。

本机迁移后的操作命令为：

```bash
python3 -m dingtalk_bridge.service_manager status
python3 -m dingtalk_bridge.doctor --agent-config local/agent-config.json --agent-config local/agent-direct-config.json --live
# 维护时使用；先确认没有进行中的任务
python3 -m dingtalk_bridge.service_manager stop
python3 -m dingtalk_bridge.service_manager --agent-config local/agent-config.json --agent-config local/agent-direct-config.json start
```

## 归属、失败与回退

管理记录为 `local/runtime/managed-processes.json`，日志为 `managed-transport.log`、`managed-agent-N.log`，生命周期事件为 `manager-events.ndjson`。记录、锁和日志使用0600，包含本机私密信息，不分享。文件原子替换，启动/停止通过独占锁串行执行。

启动先做离线配置诊断，再依次启动传输、gateway。传输必须有本次进程的监听日志及鉴权健康响应、实际路由集合匹配；gateway 必须打印本次 ready 日志且存活。ready 不等于模型成功执行。进程归属同时核对 PID、启动时间、完整命令；macOS 的 Python launcher 切换完成后记录最终身份。陌生端口和归属变化均拒绝接管或发送信号。

启动失败仅按逆序停止本次新建的子进程，已经运行的受管组件保留。正常停止为 gateway 逆序后传输，只发 SIGTERM，不强杀进程组或共享 DWS bus。超时保留记录和私有日志；`--timeout` 为每个组件的1–120秒。没有开机自启、守护进程自动拉起或进程创建与记录之间的崩溃原子性；若管理命令在极窄启动窗口被强杀，需独立核对遗留进程，不能删记录后盲启。

本次一次性迁移先用旧 `agent_ctl.py`/`service_ctl.py` 停止其拥有的三个进程，然后才用新管理器启动。旧 PID 文件保留历史，不再代表现运行进程；**不要用旧脚本管理现在的服务**。若仅需回退管理方式，先用新管理器停止并确认全部 stopped，再用旧脚本依次启动传输和两个 gateway。沿用当前代码和原状态，不回滚数据库、不删游标、不重放任务；回退到缺少拒绝审计/长文修复的历史代码不在本次验证范围。

## 验收证据

- 新增11项生命周期测试使用真实受控子进程，覆盖相同 PID 复用、持久归属停止、陌生 PID 不误杀、端口占用、配置变化、并发锁、启动失败只回滚新进程、前置检查无写入、macOS 启动过渡。首次全量暴露过渡身份错误，修复后119项全量通过；失败原日志仍留本机。
- 从不含 `local/` 的干净源码导出构建新 wheel、新 venv 安装；空目录验证六入口，缺配置启动退出且不创建状态；17个模块摘要均与当前源码一致。运行中的子进程使用该 venv 的 Python；在源码检出目录执行 `python -m` 会读取工作目录包，其字节已与 wheel 对齐。历史 docs/35 的 wheel 未冒充最新版本。
- 现场先验证未受管端口拒绝；迁移后三组件 ready、重复 start PID 不变，随后真实 stop 全部结束、start 使用新 PID，事件顺序正确。重启前后35旧任务、81旧 Agent 投递、94旧传输投递及83份运行文件保持，没有触发旧执行。
- veil 原生钉钉私聊发送一个新“19×31并写文件”任务；Kimi 实际 Write，liev 的接收/正文/文件三投递确认，无回声新任务。客户端可见带“通过AI发送”的35B文件卡片，通过原生保存框下载，再用 Finder Quick Look 打开两行 `DAB-MANAGER-20261111`、`19 * 31 = 589`，字节与生成件完全一致。本次独立短文字气泡未在视口单独观察，不用历史回读冒充该项UI证明。

[只读审计](../scripts/accept_service_manager.py)有39项检查；删除一个确认回复、破坏客户端下载内容的两项内存负向注入均被识别。公开记录：[账本](../evidence/2026-11-11/service-manager-ledger.json)、[安装](../evidence/2026-11-11/service-manager-install-validation.json)、[UI观察](../evidence/2026-11-11/service-manager-ui.json)、[审计负向验证](../evidence/2026-11-11/service-manager-audit-validation.json)。原始进程记录、截图、AX、账号账本只在本机 `local/service-manager-20261111/`。

原24h观察器未重启，迁移维护记入原 run。此检查点511样本、约4.25小时、累计3个不可用采样；维护停机可能落在采样之间，不能因本段未新增不可用采样宣称无中断。24h尚未完成，网络分区、凭据过期、引用/完整长文气泡、群新增范围及办公闭环仍按活动计划继续。

## E027部署补记
137回归与新wheel六入口/18模块已过，当前三进程已加载引用发送实现。停机时出现PID变化保护错误，后独立status为全部stopped，才正常启动；未强杀，错误原样保留。原观察器不重置，维护累计6不可用，详见[docs/46](46-quoted-text-reply.md)。
