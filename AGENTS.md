# 钉钉 bridge 工作约定

## 续作入口与目标

只在`/Users/veil/Projects/dingtalk-agent-bridge`修改本项目；聊天入口目录不是代码库。沿用当前checkout与`codex/complete-bridge`分支，不修改`/Users/veil/Projects/wecom-bridge`等参考库，不复制其账号数据，不远程发布。

每轮先读`plans/completion/`中的CURRENT_MISSION、MODE、PREFLIGHT、CRITICAL_PATH、TODO、EVIDENCE、PROGRESS_LEDGER、99-执行偏差日志。需求级别以01-PRD为准，逐格结果以ACCEPTANCE_MATRIX为准。文档13/17和README是当前摘要；历史检查点见[原文存档](docs/history/through-E035/README.md)，不要将历史“下一步”当新任务或重复开测。按实际关键路径再读对应阶段文档，最近为docs/52–54。

交付通用普通账号IM工具＋真实本地Agent接入：群聊/私聊交办、文件原件、实际工具执行、多轮上下文及同会话交付。CLI/HTTP/consumer不绑定组织或runtime。至少一个本地执行器即可；Kimi真实Read/Write/Bash已满足，Codex请求超时单独跟踪，不额外制造双runtime门槛。

## 授权与当前范围

- 用户已明确授权DWS的liev行为与原生钉钉客户端veil行为，可合成文字、文件、任务、恢复实验并下载打开。liev是**真人普通账号**，DWS `--as user`；`[Agent]`是文本前缀，客户端显示liev和“通过AI发送”，没有创建bot。
- 仅原测试群和veil/liev两人私聊。11月11日20:53发现原群由2人增至3人，范围确认问题已发但未答；新增群实验暂挂，继续私聊及独立工作。不是缺第二账号，不重复索取已授权私聊权限。未授权第三人、全组织监听、成员/权限变更、新bot或远程发布。
- 两路精确绑定liev profile，selfSenderId及veil白名单由现场身份核对；不跟随DWS默认profile静默切换。组织/profile是配置，不是产品固定租户；旧周威/legacy账本原位保留，不迁到新身份。群普通消息不执行、群任务需`/agent`，私聊文字/附件可交办；liev自身回复不触发。
- 只在当前本地任务工作区运行。Kimi提示词及官方工具上下文不是OS沙箱，不宣称对任意不可信联系人安全。

## 官方与自研边界

固定官方DWS v1.0.67在`local/bin/v1.0.67`，全局旧v1.0.61保留。官方负责身份/权限/profile、聊天/历史/资源和办公API；bridge补路由、白名单、任务/会话、幂等投递、文件及恢复。没有必要时不重造官方能力。

原生image需本地CHAT_IMAGE上传的明确缺口：隔离补充叶子复用固定官方源码上传/鉴权，原版binary不改，PNG/JPEG ≤2MiB；更大图片作为file交付。输出单文件20MiB是bridge策略，超限failed并提示压缩/拆分，不自动改写产物。WAV/MP4 file原件可传，MP4客户端可播放，均不能外推语音条/独立video协议。

官方已有bot的dev connect/OpenClaw及数字员工路线，与liev普通账号路线分开。会议/钉盘/外部/bot未实测项保留；不创建新身份代替验收。DM仅显式启用officialDwsTools，群关闭；上下文不授予额外权限。官方契约、源码、API、原件、UI和独立对端证据分别陈述。

## 运行、状态与恢复

当前HTTP为127.0.0.1:18768，两路stream_hint唤醒history，15秒补读兜底。三个进程由`python3 -m dingtalk_bridge.service_manager`管理；status只读，start须显式选入两个`--agent-config`。旧`*_ctl.py`及PID文件不管理当前进程，无开机自启。当前配置/私有归属均在local，不从历史PID猜控制目标。

E035版本已加载两gateway；156回归、干净wheel六入口/18模块摘要通过。当前快照DM46任务114outbox（113确认1旧拒绝）123传输170事件；群3/7/12/76。数字只代表E035快照，续作先只读对账。E034增加quote来源元数据，缺失senderId保持null，显示名不成为身份或执行授权；旧模型不重写。

原24h观察`run=reliability-20261111`起点11月11日19:36:08，PID97881；必须核对进程命令/新鲜采样，不能删除、重启覆盖原样本。最早11月12日19:36后评估，终检用`review_service_observations.py --require-complete`。E031完整性审计已实现，但未满24h；6不可达/3poll_error及维护窗口保留，不能宣称同版本零中断。E028只证明自然access预刷新和后续同步，不代表失效refresh恢复；禁止复制/改写token、改时钟或撤真实授权来造故障。

## 验收与推进规则

1. 原生UI交办、实际runtime工具、liev可见回复、客户端下载并打开/解包，分别取证。API成功、历史回读、测试数量或文档数量不能替代UI通过；未知/不支持/阻塞不改绿。
2. 合成实验用DAB标记和稳定幂等键；未知先对账，禁止换key或切UI补发。已确认实验只读复核，不重跑。旧blocked/cancelled/failed/rejected及错误结论不删除：E032/E033的错误SHA及首次误判、E024模型违约、E035原超限failed均保持。
3. 代码修复有相应回归/验证；按功能/验收小步本地提交，更新当前状态、证据与manifest。共享核验`verify_handoff.py --write-manifest`后再次只读核验；`verify_privacy.py`扫描暂存blob。私密账号ID、令牌、OAuth、签名URL、原始聊天、AX及截图只留local，绝不入Git/公开上传；合成fixture可共享。
4. 每轮约45分钟目标上限，实际推进代码/工具/真实UI，不只巡检或重制定计划；完成一段继续无依赖项。相同路径两轮无新证据触发loop guard。入站引用旧右键/坐标/Command+Up/设置/侧按钮路径已无新结果；只有明确新入口再试。E027 during-shutdown身份保护错误仍未定位，E030只修pre-signal退出竞态，不混称已修。
5. 单Agent，不自行派子Agent。正常未变化时安静；仅实质里程碑、失败、完成或必要用户动作汇报。MUST、完整自检与真实24h全部满足才标完成并停用heartbeat；当前未完成。SHOULD缺口保留原级别。
