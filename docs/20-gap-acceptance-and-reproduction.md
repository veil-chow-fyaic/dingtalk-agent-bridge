# 单人缺口验收与复现配方

日期 2026-11-11；隔离 DWS v1.0.67；唯一已授权内部测试群、成员1、本人办公对象。无需第二成员。本页记录当日较早的单人新增实验（当时17项回归）；后续通用工具与本聊天续作见[docs/22](22-generic-tool-and-consumer.md)、[docs/23](23-continuation-and-migration.md)，当前共39项回归。原始六种媒体基线见 docs/14，首版服务实验见 docs/16。

## 执行、验收、保留结果

| 用例 | 判定依据 | 结果 |
|---|---|---|
| DOCX 926 B | 发送 SUCCESS，精确消息下载，原件 SHA256，AX 文件卡片 | 通过；未验证 Word 编辑/渲染 |
| XLSX 1577 B | 同上，AX 显示对应文件名和大小 | 通过；未验证 Excel 公式/编辑 |
| 一条消息两张不同 PNG | 两个 mediaId，两个原件摘要一致，客户端分别看到两张内联图片 | API 与本机显示通过；没有独立对端验收 |
| 引用 XLSX | reply delivered；客户端气泡引用目标文件名 | 通过 |
| 本人日程 | 创建后按 eventId get，标题、时间、FREE、仅 self 一致 | 通过；附带 onlineMeetingInfo 和默认提醒；未入会 |
| 未发送草稿 | 取 result.message.id 回读正文；to/cc 空 | 通过；未发送邮件 |
| 服务停止期间补读 | 停止实验服务→官方发送一条→查成功→重启→sync两次 | 找回该条且仅一个事件，from_self=true；第二次 inserted=0 |
| 本地故障回归 | 17项 unittest | 通过，包括缺 sender 不误判他人、string false 业务错误、部分历史重启恢复、探针不重复副作用 |

本轮新增5条测试群消息（办公附件2、多图1、引用1、停机补读1），账本18条事件。之前的13条仍保留。另保留过去时段本人日程、无收件人草稿；之前的本人文档与已完成待办保留。没有删除业务对象、修改组织成员、邀请他人或开启全会话监听。

## 证据

- [API 与办公验收](../evidence/2026-11-11/gap-acceptance.json)
- [本机 UI 观察](../evidence/2026-11-11/ui-gap-acceptance.json)：只记录测试群观察，未将带其他业务侧栏的整屏截图存入知识库。
- [停机补读](../evidence/2026-11-11/restart-gap-acceptance.json)：本轮有界操作8.6秒，不把它称为长断网、24/72h soak 或 Stream 补发。
- 原始精确对象/任务/资源记录在忽略的 `local/probes/`，默认私有权限。公开证据只保存脱敏结论。

## 复现步骤

1. 先读 [开通手册](11-onboarding-lessons.md)，按 `config.example.json` 建立自己的 `local/service-config.json`；版本、profile、群 ID 和 selfSenderId 须实际核对。官方二进制放配置指定路径。
2. 只读复核使用 `python3 scripts/service_ctl.py status`；本地回归使用 `python3 -m unittest discover -s tests -v`。这两项不发送测试消息。
3. 有明确新实验意图时，运行 `python3 scripts/gap_acceptance.py --execute --run-id <新实验编号>`。将产生4条群消息、1个本人日程和1个未发送草稿；日期/标题目前固定为本次样本，复用于其他时间须先检查脚本，并保持日程为过去时段且无其他参与人。
4. 停机补读使用 `python3 scripts/restart_gap_acceptance.py --execute --run-id <新实验编号>`，会短时停止/恢复本项目服务并发送1条限定群消息。应在该实验服务独占、没有业务自动回复时运行。finally 恢复服务；恢复失败查本地日志，不能强杀共享 DWS bus。
5. 每个请求先写 durable intent；同编号同请求返回原结果；参数或 profile 变化拒绝；失败/未知不自动重发。首次历史记录早于 fingerprint 字段，现会保守拒绝重跑并保留原证据，请读 summary.json。**不得为了绕开未知状态随便换 run-id。**先按任务/消息 ID 对账，只有新实验意图才新建编号。
6. API 投递确认、历史正文/资源、下载摘要、本机呈现、独立对端实收逐层记录。只做到了前几层时不得补写剩余层“通过”。

## 文档与待办配方（当前实例已完成，不再创建）

下列是新环境复现用的参数顺序，省略的 profile 和真实 ID 必须从本机认证/上一步结果获得。每个写入先保存意图和返回 ID。

- `doc +create --name <DAB测试名> --content <初始标记> --yes` → `doc +update --node <返回ID> --command append --content <追加标记> --yes` → `doc +fetch --node <同ID>`，检查两个标记。fetch 的确切参数见对应版本 Help。
- `todo +create --title <DAB测试名> --executors <已核实本人userId> --yes` → `todo +complete --task-id <返回ID> --yes` → `todo +get --task-id <同ID>`，核对 isDone。不要用 senderId 替代 executor userId。
- mail/calendar/minutes/drive 的配方、默认副作用及限制见 [办公工具](19-office-tools-and-permissions.md)。

## 本轮发现并修正

- `chat +messages-send` 的文本参数是 `--text`；`+messages-reply` 使用 `--content`。首轮停机补读误传 content，CLI 在参数解析阶段 exit=3、ambiguous_flag，未产生任务；保留失败证据、修正为 text，沿用同一个发送幂等键后通过。不能把参数拒绝写成钉钉发送权限问题。
- 某些 DWS 业务返回 success 为字符串。实验服务现在同时拒绝 false 和 "false"，包括外层和已识别 envelope 内层。
- 消息缺 senderId 时 from_self 必须为 null，不能因为不等于本人 ID 就标为他人；已修正并测试。
- 探针保存请求 fingerprint，拒绝编号不变但参数变化。超时和进程中断的意图不自动复用。

## 未通过范围

另一账号入站、非 @ 群触发、人与人私聊、跨组织/含外部成员群、外部客户、独立收件人实收：skipped_by_user。原生语音条/视频消息、长断网/令牌到期恢复、24/72h稳定性、纪要正文/钉盘普通文件、真实团队 runtime 挂接：未完成。它们保留在 [执行清单](13-roadmap-and-backlog.md)，不由单人结果代替。
