# veil 发任务、liev 回复：双账号客户端验收

## 2026-11-12 E025：既有CSV客户端补验

原E001已回传CSV，但当时仅下载打开了三份TXT。此次在原私聊原生搜索的“文件”页定位`0-dab-ui-input-summary.csv`（79B），返回原聊天文件卡片下载，保存后用Finder Quick Look实际打开为表格，核对两行小计36、18及TOTAL54。下载件与原Kimi产物SHA-256一致。没有重新发任务、文件或其他聊天消息；群/私聊任务、outbox、投递账本逐行不变。

22项只读检查和损坏下载/缺失打开UI两项负向检查通过；复核`python3 scripts/accept_csv_client_open.py`，结果在[evidence](../evidence/2026-11-12/csv-client-open-ledger.json)和[审计负向验证](../evidence/2026-11-12/csv-client-audit-validation.json)。原AX、截图、下载件在`local/csv-client-open-20261112/`。点击下载时CUA超时，重新观察确认保存窗口已打开后完成保存，没有再次点击下载。

同段引用新入口只读检查：原生“修改”菜单仅编辑命令，“帮助”仅钉钉帮助，没有明确引用/回复命令；未发引用消息。原树在`local/quote-menu-20261112/`。右键等旧失败路径未重试。最新逐格范围见[验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)；以下保留E001原日期、数量及部署叙述，当前管理命令以docs/40为准。

2026-11-11 17:13–17:28，macOS 钉钉。用户明确授权：客户端登录 veil（当前组织显示周威），DWS 授权 liev，用这两个真人账号做私聊和原测试群验收。两人均由用户安排，助手没有邀请、审批或改组织权限。

## 结论与身份

当前运行的发送者是 **liev 真人账号**，调用 DWS `chat +messages-send --as user --profile <精确账号profile>`。客户端发任务的是 veil，回复在 veil 界面的左侧，显示 liev / liev(liev)，并带“通过 AI 发送”。`[Agent]` 仅是正文前缀，没有创建独立 bot。

不能笼统说所有 DWS 都是人的身份：当前 user 路线如此；DWS 也有 bot/webhook 分支及官方 `dev connect`。它们需要各自的身份、配置和会话覆盖验收，见 docs/25。当前项目只验证普通账号路线，不把其他路径算作通过。

发现并修复的部署问题：用户切换 DWS 默认账号后，原 bridge 仍显式指定旧的周威 profile，不能自动跟随。已停止旧部署、保留原账本，使用精确 liev profile 重新解析身份与会话，绑定原群及 liev 视角的周威私聊。最终以实际请求/回复 sender ID 核对角色，没有只按展示名判断。旧数据保持不动，新账号使用新路由与 Agent 状态目录。

## 真正操作了哪些 UI

所有下列任务输入均通过 veil 的钉钉客户端输入框/发送按钮；CSV 是在访达选中合成文件、复制到钉钉输入框粘贴后发送。没有用 DWS 合成这些用户任务。

| 场景 | UI 输入与验收结果 |
|---|---|
| 私聊普通文字 | 不带 `/agent`，发送 `DAB-UI-DM-002`，liev 左侧回复 `41 × 17 = 697`，回传 TXT |
| 群聊显式任务 | 原群两人，发送 `/agent [DAB-UI-GROUP-002]`，liev 左侧回复 `29 × 23 = 667`，回传 TXT |
| 私聊连续上下文 | 第二轮 `DAB-UI-DM-003` 不重述暗号，liev 回复 `蓝鲸482` |
| 群/私聊上下文分开 | 群任务回复“不知道私聊暗号”，群/私聊实际 Kimi 原生 session 不同。这是正常会话隔离验证，不是恶意越权或 OS 沙箱证明 |
| 普通群消息不触发 | `DAB-UI-IGNORE-001` 无前缀，已进入消息账本但没有创建执行任务 |
| 上传附件→处理→交付 | UI 上传53字节 `dab-ui-input.csv`；liev 下载原件与本地素材摘要一致；自动处理附件及随后文字要求，算出36+18=54，回传 CSV/TXT |
| 用户获取交付件 | 三个 TXT 均从文件卡片点击下载、系统保存，再点击打开，在 TextEdit 核对标记及697/667/54；下载件与生成件 SHA-256 一致 |
| 身份、循环与路由 | 5个任务均为授权 veil 非自身消息；14条确认投递全部来自 liev，分别回原会话；无自身回复触发的新任务 |
| 重启恢复 | 已完成任务、outbox、session、执行日志在受控重启前后保持一致；没有重跑任务/重复投递，证据见下 |

本轮5个执行任务=群1个＋私聊4个。私聊4个包括“只上传附件”和随后带计算要求的文字两个独立任务；这反映当前产品行为：没有把短时间连续的附件与正文合并成单个任务。后续可改为显式引用或合并窗口，但不能把当前两次执行伪称单次。

UI还揭示：即使 liev 已经处理并回复，veil 的原消息仍可能显示“未读”。DWS读取/Agent完成与钉钉已读回执是不同状态，不伪造已读，不以它代替实际对端回复。

## 证据与无副作用复核

- [账本、身份、原件和重启检查](../evidence/2026-11-11/two-account-ui-ledger.json)：由只读脚本重新计算。
- [人工观察的UI步骤、截图摘要](../evidence/2026-11-11/two-account-ui-observations.json)：明确是原生 UI 观察，不让后台脚本冒充视觉验收。
- 原始截图、AX、实际下载件：`local/ui-two-account-20261111/`。含侧栏个人会话与账号信息，不进入共享 manifest。
- 原来的单账号 UI 验收仍在 docs/26 与独立 evidence 保留，仅代表当时周威自发自收。

```bash
python3 scripts/accept_two_account_ui.py
python3 scripts/agent_ctl.py status
python3 scripts/agent_ctl.py --config local/agent-direct-config.json status
python3 scripts/verify_handoff.py
```

以上不会发送或重放消息。账本检查不能替代重新操作客户端；它只校验已发生的这批有明确标记的任务。更换部署或删除本地原件后，不应照搬当前断言。

## 当前运行与尚未通过项

传输服务仍监听127.0.0.1:18768，两个 liev 路由，15秒有界历史轮询。群 gateway 用 `local/agent-config.json`；私聊 gateway 用 `local/agent-direct-config.json`。都只允许 veil 的已核验 sender ID，`allowSelfCommands=false`；不对全组织/任意私聊开放。群使用 `/agent`，私聊可直接发文字/附件。

新配置 `initialCursor` 只为全新 consumer 设置一次历史起点；本轮群49、私聊1条基线不执行。重启以持久cursor为准，修改该值不会跳过已有 consumer 的新任务。`agent_ctl.py --config` 为各配置隔离PID/日志，可分别启停。新增两项回归保护历史不重跑和cursor合法性，当前73项通过；这些自动测试仍不冒充UI验收。

Codex adapter保留，但此前真实请求超时未解决；本轮实际执行器是Kimi。没有原生语音条/视频发送、完整Stream业务接收、bot UI闭环、外部客户覆盖、办公工具全面接入、24/72小时稳定性或恶意多租户安全验收。Kimi当前执行没有OS级沙箱，工作区提示词不等于强隔离。上述缺项不能用本轮成功外推为“所有情形都通过”。
