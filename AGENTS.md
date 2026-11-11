# 项目工作约定

当前交付目标：通用钉钉IM工具＋真实本地Agent接入，群聊/私聊交办任务、附件、多轮上下文和结果交付；不绑定组织或runtime。先读README、plans/completion/INIT.md与CURRENT_MISSION.md、docs/28（最新媒体与事件）、27（双账号基线）、17（总状态）、13（摘要）、25（官方边界）、15（运维）。docs/07、14、16、23、24、26中的历史数量和部署不要当当前配置。

## 最新授权与真实部署（2026-11-11）

用户明确将DWS授权改为liev，客户端登录veil（当前组织显示周威），授权用veil向liev发私聊和原群任务、查看liev回复。旧“单人群/跳过私聊与多人”限制已被这次明确授权替代；仍仅限这两个指定账号、原群及其私聊，不扩成全组织/任意业务联系人。用户自己添加liev和群成员，助手未邀请/审批。

当前发送主体liev真人账号，DWS --as user，非bot。[Agent]仅文字前缀，客户端左侧显示liev回复和“通过AI发送”。DWS默认profile切换不会覆盖bridge显式绑定；不能静默跟随默认账号。两个活跃路由均精确指定liev profile，selfSenderId/允许veil的sender ID按当前上下文重新解析并以实际收发核验。

本轮通过真实UI输入/发文件：群667与TXT；私聊697与TXT、多轮蓝鲸482；CSV上传后合计54及TXT。三个TXT均客户端下载、TextEdit打开且SHA-256与生成件一致；群普通消息不执行、回复无循环、群私聊原生session分开。5任务（群1/私聊4）、14确认投递、70事件快照；只上传附件会单独触发任务，后续文字另一个任务。UI有些任务已回复但原消息仍未读，不能将DWS读取当已读回执。73项自动测试与UI证据分层。

真实配置local/service-config.json含两个liev路由，各自新状态目录。原周威单群配置备份local/ui-two-account-20261111/previous-*.json，旧legacy账本原位保留且不再激活；禁止将旧stateStorage=legacy迁到新profile。新gateway initialCursor仅初始化全新consumer一次（群49/私聊1），重启持久cursor优先，不回放旧任务。

127.0.0.1:18768传输服务，15秒history轮询。群gateway local/agent-config.json；私聊gateway local/agent-direct-config.json。scripts/agent_ctl.py默认管理群，--config local/agent-direct-config.json管理私聊，各自PID/日志。均仅允许veil且allowSelfCommands=false。无开机自启。实际runtime是已登录Kimi；Codex CLI已登录但真实请求超时，adapter保留。Kimi工作区提示词不是OS沙箱，不能开放任意成员执行。

## 证据、身份和资料边界

必须从钉钉客户端UI发任务、看可见回复、下载打开文件。API成功、历史回读、单元测试不能冒充用户侧验收。当前双账号UI证据见docs/27，原单账号UI历史见docs/26。local/ui-two-account-20261111和local/ui-acceptance-20261111的原始截图含私人侧栏，仅本机保存，不纳入共享manifest。令牌、OAuth、账号配置、签名URL、未筛选业务消息也只放local/。

固定实验DWS v1.0.67在local/bin/v1.0.67，保留全局v1.0.61。官方优先：DWS负责身份/权限/profile、聊天/历史/资源、办公API；自研补普通账号任务队列、会话、白名单、文件、幂等和恢复。官方已有dev connect机器人到本地Agent、OpenClaw Connector，不再声称bot接入全须自研。没有创建bot。

普通账号覆盖外部业务的动机保留；bot类型需独立调查，不照搬企微规则。官方契约、源码、上游报告、服务端实测、UI、独立对端分层。Stream ready不等于业务入站，file不等于原生音视频，用户读取不等于标记已读。当前未通过：Codex实际执行、原生音视频、Stream与服务唤醒集成/断连恢复、bot/外部客户UI、完整办公接入、24/72h可靠性、恶意隔离。

## 持续工作规则

在本项目修改代码资料，不修改参考/Users/veil/Projects/wecom-bridge或复制其他项目账号数据。本地Git已初始化，分支codex/complete-bridge，基线166b11b/tag baseline/ui-2026-11-11；未发布远程。pre-commit运行暂存内容隐私检查和handoff核验。活动执行计划只有plans/completion，docs/13为摘要。

实测用DAB标记和稳定幂等键；未知先对账，不换key或切AX重发。已完成写入实验不重放，复核优先scripts/accept_media_matrix.py（只读）；accept_two_account_ui.py是此前基线的全量任务审计，新发现保留的blocked会令其all_jobs_completed为false，不能删除失败来变绿。共享交接scripts/verify_handoff.py；更新后显式--write-manifest并再次核验。单元回归和UI验收都需真实结果，不用文件数量或测试数量代替完成。

继续独立推进，不把阶段汇报当停工理由。不要重新索取已经授予的这两个账号测试权限；真实外部依赖如实记录，不能称全项目或所有情形均完成。

## 2026-11-11 19:05续跑检查点
PNG/PDF群/私聊双向8案例、10资源摘要一致；私聊PDF客户端下载并Quick Look打开。真实有限Stream捕获群5/私聊11事件，全部匹配history、无重复，退出码0；这不是常驻服务已启用Stream（当前仍history）。真人PNG的双资源别名曾使一条DM任务blocked；已以下载SHA相同证明别名再合并语义，未知/不同内容仍拒绝。新DM图在前/群图在后任务均完成320×180并UI核对；原blocked保留审计，不静默重跑。完整复核scripts/accept_media_matrix.py；docs/28。76项自动测试。长期任务heartbeat id=bridge，每30分钟附着当前聊天，机器/Codex在线时续跑；无新结果保持安静。
