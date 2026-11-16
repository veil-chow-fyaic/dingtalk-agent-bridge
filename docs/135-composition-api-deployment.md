# 通用IM组合部署与两路真实API原件验收

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-16，E134。沿原PRD、矩阵、最终自检和codex/complete-bridge单Agent推进。已部署E133产品2467fe2，完成AIC群及原私聊各一条文字＋两张新PNG的真实发送、历史回读和官方资源下载。此轮没有模型请求或新增Agent任务，Kimi服务拒绝不构成这些通道工作的前置阻塞。

## 部署与账本边界

北京时间11:12开始维护，11:15恢复全部受管服务。部署前23个产品模块与E133冻结源验证摘要一致，工作树干净、配置摘要和两路runtime绑定明确；99任务、240 Agent outbox、所有传输投递均无未决。先按manager实际归属停两个gateway，再封新DWS调用、排空两槽并停transport，保存六库。

通用prepare_history_deployment计划器拒绝sqlite_sidecar_requires_separate_review：六库均有0字节WAL和32768字节SHM。原拒绝及当时operator_suspended/全部停止状态保留，没有删旁文件、checkpoint源库或修改计划器。单独审查在持有manager、DWS准入、每路bridge/consumer拥有者锁且全部数据拥有者停止时，用只读SQLite事务、quick_check和backup读取一致性快照；核scope、runtime binding、完整任务/meta/outbox、inbox、零未决和零候选积压。该独立审查通过不等于原计划器通过。

随后仅启动transport，固定cut为2026-11-16T03:14:23.724287+00:00；在每路同一个SQLite快照中确认watermark达到cut且无history_window。再次封调用/排空/停transport后审积压，才恢复两个gateway。最后三个服务均按原manager运行、DWS准入ready、两路同步complete且无poll_error；这是本轮捕获状态，不是连续健康或自然refresh证据。

产品代码从旧e7d82cc更新到2467fe2，没有改变DWS v1.0.67、profile、会话、history-only15秒、Kimi/Pi配置、网络环境声明或绑定。23模块包含OpenClaw适配代码，不能继续称该代码未部署；但没有启用OpenClaw绑定、调用真实provider或验其UI。未来文档提交HEAD不代表部署产品。

## 群聊和私聊的新组合样本

每路分别生成两张不同的160×96合成PNG（共四个新原件），保存各自SHA与单一业务key，顺序调用已部署POST /v1/send的composition。两次均HTTP200、state=confirmed，有官方task/message回执；每路只新增一个传输delivery和一个history消息，无重发、补发或模型任务。

历史投影均为文字、image1、image2，无issues；文字与原意图一致，两图顺序保留，精确account/conversation及from_self=true。POST /v1/attachments沿官方+messages-mget --download-resources，各回两原件，ok=true、partial=false、failedCount=0；四个源文件、摘要暂存和官方回读下载逐字节相同，SHA256和字节数一致。资源身份按history的有序引用对应，不能用无序摘要集合代替顺序。

gateway consumer也持久收到了这两条自身消息，模型投影正确、state=pending_media、attempts=0、无error。自身消息按设计不hydrate或交办；本轮单独对官方下载结果做离线materialize，不修改受管inbox，也不声称它已normalized/ready。前后全部任务库（含meta/session/binding/jobs/outbox）逐行一致，仍99任务/240 Agent outbox。旧传输及inbox记录完整保留。

## 验证与尚缺证据

[只读审计器](../scripts/accept_composition_api.py)以保存的快照、回执、history、下载清单和四组捕获字节做34项检查，并用5个篡改负例拒绝acked冒充confirmed、下载字节改变、图序改变、未完成history_window和session账本改变，全部通过。[脱敏证据](../evidence/2026-11-16/composition-api-validation.json)记录范围。此轮无产品源码更改，不重跑E133冻结源/同wheel双Python各448方法、旧CLI/宿主/观察；34＋5是本轮真实证据审查，不加入产品测试总数。

原生DingTalk UI本轮仅尝试读取一次，仍返回-10005/failedToCreateImageDestination；加上E133已连续两轮同路径无新界面，停止重试。没有权限变更、系统重启或其他工具绕过。因此未观察这两条消息的客户端完整显示、发送者/AI标识、逐图保存及打开。API官方下载成功不能替代这些用户视角证据，也不能推成原生image卡片、普通文件组合、9图/JPEG全范围或模型理解通过。E011旧原件获取失败、E056仅计划、E131模型失败均保持。

矩阵仍51通过/11阻塞/2部分，R01/R04/R06/R07/R12/R13/R14七MUST未完整。UI恢复有新可读证据后，核对E134既有两条消息及保存原件，不为补截图重复发送。其余普通多文件、私聊入站引用、原生voice/video、R13自然续期/长期/截止仍各需对应入口或业务证据；群模型独立等待既有Kimi访问恢复，不再探测或重发E131。最终当前版交接仍待全部标准满足。

原始回执/会话/配置/日志/数据库/下载与一次性驱动只在local/composition-api-20261116及local/outbox/composition-api-20261116。六份最后数据库分别backup，不是跨六库共同原子快照，也不是旧观察截止。没有认证修复、凭据复制、runtime迁移或远程发布；不照抄本轮local驱动重复部署。
