# 验证协议与当前用例矩阵

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-11。当前组织/群均为深圳市弗忧智能科技有限公司，稳定ID已私存，INTERNAL_GROUP、成员1。旧aic群AX冒烟独立保留。DWS v1.0.61基线与隔离v1.0.67结果分开。本轮新增证据见 [docs/20](20-gap-acceptance-and-reproduction.md)。

## 身份与执行顺序

桌面登录、CLI OAuth、profile、群类别、消息senderId分别确认。个人事件的self-loop语义意味着本人发送/回读不能证明另一成员入站。用户已要求跳过多人现场项目，以下依赖他人的步骤只在恢复范围后使用。

固定版本与Help → 管理员CLI开通 → OAuth/profile核对 → 唯一会话绑定 → 少量只读历史 → 合成消息发送与原任务查询 → 资源下载摘要 → 客户端呈现 → 独立对端实收。事件测试另需监听ready后真实入站、对照事件/历史时间、正常退出并确认订阅与消费者清理。

只在实际失败格子探索AX。未知投递保持unknown并查原任务，不能换key或跨后端重发。完整性是单独验收项，CLI exit=0、监听ready或台账discovered=0都不是完整成功的充分条件。

## 用例矩阵

| 用例 | 通过标准 | 当前状态 |
|---|---|---|
| AX-TEXT | 本地气泡匹配/草稿清空 | 旧群冒烟通过；新群官方路径已通，暂不新增AX发送 |
| IN-TEXT / IN-AT | 另一人普通非@及原生@消息真实进入事件，身份正确 | skipped_by_user |
| IMG-PLAIN | 原件、资源引用和UI可识别 | 本人纯图API已测；他人纯图事件未测 |
| IMG-RICH / MULTI | 两种不同图片原件匹配、有序显示 | 本人双图API与客户端显示通过；事件及对端未测 |
| FILE | TXT/PNG/PDF/ZIP/WAV/MP4/DOCX/XLSX原件大小与SHA一致 | 本人上传/下载通过；Office编辑不在本用例 |
| AUDIO / VIDEO | 原生形态、原件、播放独立验收 | WAV/MP4附件通过；原生语音条/视频未通过 |
| OUT-MEDIA | 投递、原件、客户端/对端类型分别正确 | API及本机部分通过；对端实收暂跳过 |
| QUOTE | 引用对象正确且结构保留 | 文本引用API、XLSX引用API/气泡通过；consumer结构化引用未完成 |
| BURST | 有界突发每个原生ID入账无漏重 | 未执行10条真实突发；已测同正文不同ID不合并 |
| RECONNECT | 间隙消息重启补读并去重 | 本人短停机历史补读通过；Stream断线补发未测 |
| SEND-UNKNOWN | 保留意图/任务、对账、不重复发送 | 本地故障回归通过；真实上游超时故障未注入 |
| PRIVATE / EXTERNAL | 明确会话与身份独立端到端 | skipped_by_user，资料边界见docs/18 |
| ORG-TOOLS | 合成对象写入后按ID回读，身份/副作用正确 | doc/todo/calendar/unsent draft通过；其他见docs/19 |
| SOAK | 24/72h吞吐/延迟/缺口/恢复指标 | 未完成，短时健康不替代 |

## 命令模板

以下是占位配方，不直接复制执行。所有ID必须由同一profile实际解析；不使用all-group/all-direct。

```text
dws event +listen-im --profile <P> --kind group --chat-id <G> --events message --duration 120s --format ndjson
dws chat +chat-messages --profile <P> --group <G> --format json
dws chat +messages-mget --profile <P> --msg-ids <M> --download-resources --output-dir ./local/downloads
dws chat +messages-send --profile <P> --as user --group <G> --text <合成正文> --idempotency-key <K>
```

`--yes`只在已有明确写入意图/范围时使用。自动化复现入口见docs/20，其显式execute会产生已说明的合成副作用，不是健康检查。

## 证据与AX纪律

每条结果记录日期/时区、版本、目标类别、账号别名、输入编号、操作入口、实际任务/消息ID私有引用、发送/事件/历史时间、摘要、结果与限制、保留或清理状态。状态使用passed/failed/unverified/skipped_by_user；等待权限才单列外部条件。

本机UI已观察测试群归属、输入框、图片、文件卡片、引用；未证明AXObserver可靠、后台监听、原生音视频自动操作、任意历史完整性或专用Python进程TCC权限。元素序号随界面改变，不能复用旧坐标。单人群“全部已读”不证明独立收件人已读。
