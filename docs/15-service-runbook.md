# 实验适配服务：启动、接入与恢复

2026-11-11。代码位于 `dingtalk_bridge/`，仅使用 Python 标准库；当前liev账号的原群及veil私聊已真实UI联调。它使用官方DWS事件提示唤醒历史同步，15秒定时补读兜底；双账号入站、短停机补漏与订阅进程重连已通过，长期可靠性仍未完成的实验 bridge。

## 当前交付

- 固定 DWS v1.0.67 项目内二进制；全局 v1.0.61 保留。
- HTTP 仅监听 127.0.0.1:18768，所有接口要求本机 Bearer token。
- 支持多个账号/会话路由，每路独立状态；本机启用liev账号原授权测试群和veil私聊。启动按稳定会话ID校验，不写死组织名。配置与公共CLI见docs/22。
- 每 15 秒拉取两个限定会话历史，消息以原生 ID 去重；提供持久化游标供 Agent 消费。
- 文本、文件、PNG/JPEG 独立原生图片发送（需配置官方上传补充入口）；SQLite 保存 key、payload 摘要、任务与消息 ID。
- 已确认结果可重放查询；同 key 改 payload 拒绝。发送中断/返回不明保持 outcome_unknown，不自动重发或切 AX。
- 附件下载独立于历史轮询锁；落盘后校验摘要，缓存丢失/改变时报错。
- 文档、待办等办公操作由 Agent 直接调用同一 profile 的官方 DWS；不另造通用任意 CLI 代理。

传输服务和独立Kimi gateway当前均运行中；群gateway仅响应veil的/agent命令，私聊gateway响应veil的文字/附件，liev自身消息忽略。无全组织订阅、未注册开机自启。原始消息、令牌、数据库、任务 ID 和日志均位于忽略的 local/。此目录不能整包上传公开仓库。

## 启动与停止

从 `/Users/veil/Projects/dingtalk-agent-bridge` 执行：

```bash
python3 scripts/service_ctl.py status
python3 scripts/service_ctl.py start
python3 scripts/service_ctl.py stop
```

需要前台诊断时，先 stop，再执行：

```bash
python3 -m dingtalk_bridge --config local/service-config.json --port 18768 --poll-seconds 15
```

`service_ctl.py` 保存并核对本项目进程 PID；停止只发送 SIGTERM，不强杀共享 DWS bus。日志是 `local/runtime/service.log`。SQLite 进程锁阻止两个服务同时操作同一状态目录。重启会将遗留 executing 标为 outcome_unknown。

## 本地 Agent 进程

```bash
python3 scripts/agent_ctl.py status
python3 scripts/agent_ctl.py --config local/agent-direct-config.json status
# start/stop 也分别作用于所选配置；默认群，不会自动操作私聊worker。
python3 scripts/agent_ctl.py start
python3 scripts/agent_ctl.py --config local/agent-direct-config.json start
python3 scripts/agent_ctl.py stop
python3 scripts/agent_ctl.py --config local/agent-direct-config.json stop
```

群配置为 `local/agent-config.json`，私聊为 `local/agent-direct-config.json`；启动前先确保传输服务运行。启动会响应已配置身份和会话中的任务，不是只读观察。Kimi非交互模式自动执行工具，当前只允许veil触发liev所绑定的任务；提示词的工作区规则不等于OS沙箱。会话命令、日志、失败恢复和真实验收见[docs/24](24-local-agent-product-and-acceptance.md)。

## 配置和秘密

真实配置为 `local/service-config.json`，已经迁移至v2 routes结构，含profile、conversationId、name、binary、selfSenderId等。原周威stateStorage=legacy账本原位保留但已退出活跃配置，备份见local/ui-two-account-20261111。liev的两个新路由各自使用routed状态，禁止挪用旧账本；模板见 `config.routes.example.json`，迁移与选择命令见[docs/23](23-continuation-and-migration.md)。当前 selfSenderId 来自已确认本人发送消息的历史字段；不能把 profile userId 不经核对直接当消息 senderId。

HTTP token 首次启动生成，保存在 `local/runtime/http-token`，权限 0600。调用者从文件读取，不打印或写进源码。此令牌只能访问本机服务，不是钉钉 OAuth 凭据。

示例调用（不会发送消息）：

```python
import json
from pathlib import Path
from urllib.request import Request, urlopen
root = Path('/Users/veil/Projects/dingtalk-agent-bridge')
token = (root / 'local/runtime/http-token').read_text().strip()
req = Request('http://127.0.0.1:18768/v1/health',
              headers={'Authorization': 'Bearer ' + token})
with urlopen(req) as response:
    print(json.load(response))
```

## 接口契约

| 方法与路径 | 输入 | 结果 |
|---|---|---|
| GET /v1/conversations | 无 | 当前配置的账号/会话路由，不暴露认证profile |
| GET /v1/discovery | account_id、cursor、limit | 只读会话元数据与分页；不激活路由 |
| GET /v1/health | 无 | 最近同步、事件数、poll_scheduler触发/次数、Stream状态/业务hint、明确未验收项 |
| GET /v1/events?after=0&limit=100 | 持久化 seq 游标；limit 1–200，wait_seconds 0–30 | events、next_cursor；消费成功后由 Agent 保存游标 |
| POST /v1/sync | `{}` | 立即补读；与后台同步串行化；complete=false 时不推进水位 |
| POST /v1/send | idempotency_key + text/file/image 三选一 | key/state/task_id/message_id；confirmed 返回 200，未确认返回 202 |
| GET /v1/deliveries/{key} | URL 编码的 key | 已持久化投递状态，不发送消息 |
| POST /v1/reconcile | idempotency_key | 查询已有 task；没有 task 时仍保持未知，不猜测成功 |
| POST /v1/attachments | message_id、可选repair | 仅允许已从绑定群读到的消息；下载台账与摘要 |

多路由时会话级GET在query、POST在JSON传account_id和conversation_id；未指定或错误路由拒绝，单路旧接口兼容。

发送例子：`{"idempotency_key":"业务请求唯一键","text":"需要发送的文本"}`。图片例子用 `image:"fixtures/dab-image-001.png"`，普通附件用 `file`。必须有实际发送意图才调用；不要重放文档中的验收消息当健康探针。

文件只允许项目 `fixtures/` 或 `local/outbox/` 下的安全相对路径，解析符号链接后仍须在范围内；实验上限 20 MiB。发送前复制到按内容摘要命名的 staging。纯文本路径不接受内联图片语法，图片走独立 `image` 参数；防止消息文本意外触发本地文件读取。

事件字段包括 seq、message_id、source、conversation_id、chat、sender、sender_id、content、timestamp、from_self、attachments、raw。source 当前始终 dws_history。附件补全调用与文本消费分开；不要等待大文件下载才保存消息游标。from_self=true 默认不触发回复；未知身份不能擅自推断为他人。

## 任意Agent接入

已参考 WeCom `/messages` 与 `/ws/messages` 的事件/投递模型，但本项目暂未提供它的 WebSocket 或完全相同的请求结构。现已提供独立CLI与durable consumer：有序parts/引用/附件物化，输出仍走send。调用方选择自己的模型和业务策略。不要宣称现有 WeCom runtime 已无改动接上；当前另有本机Kimi通过gateway实际调用该服务并完成两轮任务，见[接入验收](24-local-agent-product-and-acceptance.md)。

通用consumer保持from_self过滤。当前独立gateway已完成veil→liev非自身消息的群/私聊UI闭环，详见docs/27；不对任意第三人开放。办公工具直接使用项目内 DWS 和配置中的 profile；文档/待办的真实对象引用仅存在 `local/office-objects.json`，新增日程/草稿在 `local/probes/20261111-gaps/`。公共工具接口与consumer见 [docs/22](22-generic-tool-and-consumer.md)，无需指定runtime。

## 故障恢复

1. health 的 poll_error 非空：查日志、CLI auth 和限定群只读查询，保持账本，修复后 sync。不要通过换组织或扩大群范围试错。
2. complete=false：本次最多 20 页/1000 条，不推进水位；需要调整有界补读方案。不要把部分读取当成追平。
3. outcome_unknown：有 task ID 则 reconcile；没有 task ID 保留未知并按本次合成标记/历史人工对账。不能自动换 key 重发。
4. 同 key 改正文/文件：400，属于调用方冲突；不能将同一业务重试换成新 key。确实是新消息才分配新 key。
5. 附件缓存缺失或摘要变化：报错，核对本机缓存后再处理，不静默把不存在的路径返回为成功。
6. 升级 DWS：隔离二进制、校验官方摘要，复测响应结构、发送、媒体、历史与权限；不要先覆盖可用基线。

## 已知边界

- 首次读最近24小时；后续普通水位前5分钟补读，并每30分钟进行24小时深扫描。超过深扫描窗口或读取上限仍可能漏；尚未完成长期稳定性验收。
- 当前两路已启用receiveMode=stream_hint。真实UI业务消息唤醒history、服务停机时群/私聊任务重启补漏、订阅子进程自动重连已验证，见[docs/29](29-stream-service-and-offline-recovery.md)。15秒定时补读保留；不是独立于历史索引的完整Stream接收。网络分区/授权过期/24h另验。
- 事件消费是游标式可重放交付，不承诺 exactly-once。发送已确认仅代表 API 投递状态，不代表另一人已读。
- 原生音视频在v1.0.67源码和本机dry-run均确认为file路线（见docs/23），独立语音条/video协议尚未证实；MP4通过file入口在客户端实际呈现可播放视频卡片，私聊双向原件与实际分析见docs/34。图片独立原生上传发送见docs/33；DOCX/XLSX/ZIP见docs/30–31。
- 多账号和group/direct路由已实现、确定性测试通过；指定veil↔liev私聊和原两人群已验收；外部群未验收。没有自动群管理、完整多租户权限管理或AX后端。
- 不安装自动启动或通知任务；本机重启后需要先启动传输，再分别启动群和私聊gateway。传输进程负责限定会话轮询；独立gateway会执行授权/agent任务并回复，停止自动执行需要分别stop两个gateway配置。

## 验证

```bash
python3 -m unittest discover -s tests -v
```

当前95个测试；新增Agent任务/会话/文件闭环、私聊隔离、取消等待、目录失败、越界和重启恢复；此前覆盖迁移保留账本、会话发现与选择、长轮询、订阅范围/停止、HTTP契约、媒体队列饥饿和旧探针迁移不重放。原有测试覆盖重启幂等、未知状态不重发、崩溃保留、同正文不同 ID、部分历史水位、跨会话回滚、文件边界、图片/文件身份区别、未观测附件拒绝、进程锁、CLI 新响应结构与 stderr 错误，以及缺sender保守识别、字符串false、部分历史恢复和探针请求绑定。

真实 HTTP 验收证据见 `evidence/2026-11-11/service-acceptance.json` 和 `service-restart-acceptance.json`，仅含脱敏结果。

## 原生图片（2026-11-11 更新）

路由可选 `imageUploadBinary` 指定[固定源码构建的窄补充](../integrations/dws_image_upload/README.md)，`binary` 继续原版 DWS。新 `image` 只走独立图片，不再走 Markdown；未配置明确拒绝，旧 key 仍只读返回旧回执。PNG/JPEG 原生最多2MiB且不压缩，普通 `file` 保留20MiB上限。配置后传输和对应gateway需重启才能加载。

发送回执新增 `upload_state`、`image_delivery=native`。`upload_unknown` 表示上传结果未确认且没有调用消息发送；不要换key/自动重传，官方暂无上传任务对账接口。`outcome_unknown` 表示发送阶段可能已执行，仍沿用有task ID只查询、无task ID按历史对账的规则。不要把二者都当“消息已丢失”。gateway有上传配置时，把≤2MiB PNG/JPEG结果自动作为image，其它结果作为文件。完整现场边界见[docs/33](33-native-image-bridge.md)。

安装包及只读doctor的准确语义、退出码、干净导出验证见[docs/35](35-install-and-doctor.md)。旧service_ctl/agent_ctl仍管理当前检出，不等于统一多worker管理已完成。

状态查询现以中文展示快照；自身先标完成再统计，避免空闲误报排队。实际取消和新会话UI证据见[docs/36](36-task-control-ui.md)。群和私聊gateway已一并加载该修复与原生图片结果选择，群图片新UI案例仍受原群范围待答复限制。

2026-11-11 22:39 多文件验收复核：`python3 scripts/accept_multi_attachment_ui.py`只读；已完成三请求不重发。附件独立消息各自执行，后续文字沿用同会话；文件来源/金额/结果客户端下载证据见docs/37。当前私聊generation1，旧generation0保留，本段不重启。

E018长文维护：传输和两个gateway已空闲重启加载UTF-16分段（含前缀≤5120）和新发送校验；`accept_long_text_ui.py`只读审计保留旧拒绝。当前DM有1条outcome_unknown，官方日志明确长度拒绝但无taskId，禁止换key/重投；后续补带证据的终态处置。原观察器未重置，有维护不可用采样1次。官方CLI会TrimSpace，文本尾空白不保证无损，精确内容用文件。
