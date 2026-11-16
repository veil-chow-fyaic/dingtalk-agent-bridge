# 普通账号发送组合：官方 CLI 的精确边界

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E056。固定官方 DWS v1.0.67 的 **18 个无账号 dry-run** 已完成，46 项审计与 9 个报告篡改负向通过。没有新增消息、上传、UI 验收、凭据或服务变更；当前产品仍是 E054，最近完整真实 UI 为 [E055 附件故障恢复](72-attachment-download-outage-ui.md)。这次核的是参数与计划，不能填成客户端通过。

## 已实测的命令行为

| 输入 | 官方二进制实际结果 | 接入含义 |
|---|---|---|
| 一个 `--file a.txt` | 一个文件的上传/发送计划 | 两个 action 是上传与发送步骤，不是两条消息或两份附件 |
| `--file a.txt --file b.txt`，并反向排列复核 | 两次都只保留最后一个路径 | 重复参数不是附件数组，会遗漏前面的文件；bridge 不应这样拼多文件 |
| 逗号路径、JSON 数组字符串 | 将整个值当一个路径，读取失败 | 不是数组接口；本版返回 `internal/5` |
| `--file` 与 `--file-path`；正文或 Markdown 与文件同时指定 | 参数互斥，`validation/3` | 不能用这些参数拼“正文＋普通文件”单消息 |
| `audio`、`video` 配文件 | requested 类型保留，但 effective 为 `file` | 音视频语义别名不等于语音条或独立 video 协议；此次文本 fixture 只核计划，不核媒体有效性 |
| `voice` 类型 | enum 拒绝，`validation/3` | 当前用户 shortcut 没有此类型；不据此断言所有平台 API 都不支持 |
| Markdown 两张/九张本地图引用 | imageCount=2/9，uniquePathCount=2/9 | 官方具备一条图文组合的计划，不需要自写上传协议 |
| 九次引用同一路径 | imageCount=9，uniquePathCount=1 | 引用数量与去重后的路径数量不同 |
| 十张或同一图片引用十次 | 均拒绝，`internal/5` | 9 的上限按本地图引用数，不按唯一文件数 |
| 引用式图片语法 | 拒绝，`internal/5` | 需要行内图片写法 |
| 两个普通文件 Markdown 链接 | 仍是一条 Markdown，未安排文件上传 | 链接不是可下载附件组合 |

图片探针故意使用不存在的相对路径，dry-run 仍能返回计划，因此**不能用 dry-run 成功证明文件存在、内容有效、上传成功或用户能保存原件**。正式本地图文发送还需读文件、上传及服务端/客户端验收。[官方 shortcut](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/chat/unified_send.go)

## 源码进一步确定的边界

官方先检查最多 9 个本地图引用，才进入 dry-run/实际读图；Help 中“最多同时上传 3 张”是上传并发数，并非一条消息最多 3 张。实际上传还对相同图片内容去重，dry-run 的 uniquePathCount 只代表路径去重。[引用数校验](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/chat_markdown_images.go)、[并发与去重](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/chat_markdown_image_upload.go)

Markdown 读图复用官方图片加载器，大于 2MiB、至多 10MiB 的来源可能进入自动压缩；这是源码结论，本段没有执行压缩或上传。不能把这一入口的返回内容默认为原件字节不变。[图像加载入口](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/chat_image_upload.go)、[大小与压缩](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/chat_personal_emotion.go)

官方个人文件发送只取一个路径、提交一个文件对象；audio/video 最终同样构造 file 消息。上述结论只覆盖这个固定版本的发送入口，不是对所有钉钉客户端或 Raw API 的否定。[身份能力定义](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/chat/identity_contract.go)

## 产品决定与尚未验证项

继续复用官方单文件与独立 image；多份产物逐件交付、逐件持久化状态。普通多文件单消息没有已核实入口，当前通用接口也没有承诺单消息附件数组。若后续新增图文组合接口，应复用官方 Markdown 路径，明确压缩和原件策略，并重新验收客户端获取；不能把两次 file 调用或 Markdown 文件链接标成单消息多附件。

[E011](32-native-image-versus-inline.md) 已记录内联图可见但当时无法通过查看器获取原件，独立 image 则通过。仅发现官方多图计划不能消除这项客户端限制，因此本轮不重复旧菜单或发送旧实验。E026 私聊入站文字＋两 PNG 的通过保持；出站组合、普通多文件单消息、原生语音/独立 video 仍未通过。

## 复现和证据

```bash
python3 scripts/probe_dws_send_contract.py --output local/send-contract-probe.json
PYTHONPATH=. python3 scripts/accept_send_contract.py
```

第一个命令仅调用固定版官方二进制的 `--version` 和强制 `--dry-run`；每例固定合成群目标，独立空 DWS_CONFIG_DIR，环境不继承账号凭据，也不传 profile/yes。HTTP(S) 代理指向已占用但不监听的 loopback 端口。它核官方发送参数解析，不是生产路由探针；不要删除 dry-run 或替换目标去“复核”。第二个命令只读本机冻结证据，不调用官方 CLI。

18 例最终计划见[合成报告](../evidence/2026-11-12/send-contract-probe.json)，原首次 5 个错误类别预期失败保留在 local；修正的是核验脚本的精确预期，没有改 DWS，也没有把任意报错当通过。9 个纯内存篡改覆盖 executed、dry-run、文件名、额外发送、实际类型、图片数/唯一路径数及 auth/network 伪装。两路任务/outbox/传输/事件/session/运行日志均保持，三个 manager 进程和原观察保持；原观察约 12.545h，7 不可达不变，尚未满 24h。详见[只读审计与源码摘要](../evidence/2026-11-12/send-contract-audit.json)。
