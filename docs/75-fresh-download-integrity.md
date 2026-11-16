# 首次附件下载与缓存采用同一完整性校验

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E058。此前 E054 只补了缓存命中检查；首次下载仍可能把错误字节数、重复资源或畸形清单返回为成功，并写入缓存。部分结果的 `ok:true` 也可能原样返回。Agent 的后续 materialize 会拒绝部分问题，但通用 HTTP 调用者不应依赖 Agent 层兜底。

现在首次/缓存共用资源校验：清单与状态字段的类型、资源类型/标识/唯一性、路径范围、真实字节数；首次生成本地 SHA，缓存额外比对已保存 SHA。首次路径必须在本次 attempt 目录内，缓存路径必须在本消息下载目录内。缺少必要资源或合法部分下载统一返回 `ok:false` 且不写成功清单；畸形/不完整文件数据返回 BridgeError，在 HTTP 中为502。缓存损坏继续要求显式 repair，不静默改写旧件。

repair 的新响应若校验失败，旧好清单与原件保持；后续普通读取仍可使用旧好缓存，成功的新 repair 才替换清单。这里验证的是校验失败，未将写清单中途进程崩溃或掉电原子性算作通过。

## 新验证与旧记录

- 22种首次坏响应：字节数、重复/缺失资源字段、路径、清单/消息形状、状态类型等；必须拒绝且不建立成功缓存。重启后同一消息可重新只读下载到新 attempt，旧文件保留。
- 3种部分/缺资源结果与4种坏缓存，分别核 `ok:false`、无缓存和不重新下载/改写；另测失败 repair 保住既有好缓存。
- 一个真实本地 HTTP 服务与合成 DWS CLI 子进程：首次错误字节数得到502；同消息第二次成功，第三次命中缓存，只有两次下载、两份原件均保留。
- 旧源码3方法复现16失败/10错误；旧 E057 已安装包5方法复现18失败/10错误，原日志保持。修复后相关19项、源码 Python3.14 全量189项，以及隔离已安装 wheel 在3.14/最低3.11各189项通过；六入口/19模块摘要一致。
- 现场50份既有缓存、57个资源通过新校验，只读 SQLite、禁网络对象核验，未修复/重写真实缓存。它不代表重新完成下载或UI验收。

官方固定版下载清单本身提供 `ok/partial/failedCount/downloads/sizeBytes`，并对所发现资源去重；bridge补的是接收清单后对本地文件的校验，不重写下载或鉴权协议。[官方清单构造](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/chat/chat_message.go)

三进程在任务空闲时重载，配置、两路历史任务/outbox/投递/事件、session与执行日志均保持。live doctor和24项审计通过；原观察仍同PID/起点，约12.921h、7不可达，维护另记，24h未到。没有新钉钉消息或原生UI操作，最新完整客户端链路仍是 [E055](72-attachment-download-outage-ui.md)。

## 复核

```bash
PYTHONPATH=. python3 scripts/accept_fresh_download.py
```

[24项核验及日志摘要](../evidence/2026-11-12/fresh-download-validation.json)、[冻结安装](../evidence/2026-11-12/fresh-download-install.json)。私有复现/部署/原件索引在 `local/fresh-download-20261112/`。HTTP说明已同步到[通用工具文档](22-generic-tool-and-consumer.md)和[OpenAPI](../api/openapi.json)。输入校验只保证覆盖已观察的必要资源，不将其他合法资源一概排除；引用、原生语音和普通单消息多附件的UI缺口不因此改绿。
