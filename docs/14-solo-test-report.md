# 单人群实测与下一轮闭环

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


> 历史阶段记录：保留当时版本、数量和观察。当前状态以 [总览](17-requirements-progress-review.md) 和 [最新增量验收](20-gap-acceptance-and-reproduction.md) 为准；本页的当时待测项不作为当前待办。

2026-11-11，Asia/Shanghai；DWS v1.0.61。本轮固定已有版本建立真实基线，未升级全局 CLI。当前组织和群均为深圳市弗忧智能科技有限公司，账号周威。限定查询精确匹配到 INTERNAL_GROUP，memberCount=1；其他模糊匹配结果未用作测试目标。

用户明确要求先跳过所有多人测试。因此不再以邀请成员作为推进前置条件，也不要求用户现在配合。下表是单账号能力验收，不代表其他成员入站或跨组织覆盖。

## 实际结果

| 用例 | 结果 | 证据边界 |
|---|---|---|
| 认证与精确目标 | authenticated=true，组织/账号一致，稳定群 ID 已本地绑定 | 未重新核对桌面当前选中组织；本轮完全经 DWS 执行 |
| 历史读取 | 初始 0 条，最终 7 条合成测试消息 | 小样本单页读取，未验证大规模分页 |
| 用户文本发送 | SUCCESS，取得 message ID，历史正文准确匹配 | 未验证另一成员实收 |
| 同键同正文重复提交 | exit=1；stderr JSON 报 CONFLICT_ERROR；历史该文本仍只有 1 条 | 短时间重复拒绝通过；不证明完整 24h 保留期、跨进程 exactly-once |
| TXT 文件 | 113 bytes，发送 SUCCESS，下载 SHA-256 一致 | 本人发送后本人下载 |
| PNG 文件 | 1853 bytes，发送 SUCCESS，下载 SHA-256 一致 | file 附件，不是原生图片气泡 |
| PDF 文件 | 3081 bytes，发送 SUCCESS，下载 SHA-256 一致 | 合成单页测试文件 |
| ZIP 文件 | 243 bytes，发送 SUCCESS，下载 SHA-256 一致 | 合成单文件压缩包 |
| audio 参数 / WAV | 32044 bytes，发送 SUCCESS，下载 SHA-256 一致 | 历史呈现为文件，不算原生语音条 |
| video 参数 / MP4 | 1894 bytes，发送 SUCCESS，下载 SHA-256 一致 | 历史呈现为文件，不算原生视频消息 |
| 指定群监听 | ready；45 秒后 exit=0，received=0 | 只有生命周期通过，未验证别人消息接收 |
| 退出清理 | 按本次 subscribe ID 查无订阅、无消费者 | shared bus 仍运行，显示 300 秒 idle timeout；没有强杀共享进程，未等待确认其自动退出 |

证据：[脱敏验收记录](../evidence/2026-11-11/solo-acceptance.json)。Help 保存在同目录；原始目标、发送任务与消息 ID 仅存忽略的 local/。群内保留 1 条文字和 6 个合成附件，未撤回；没有业务对象被修改。

## 两个影响实现的发现

### 发送冲突需要查账

同一个 key 重复提交不会返回原来的成功回执，而是 CONFLICT_ERROR。适配层先保存 key、payload 摘要与原始 task ID；遇到冲突查询原任务/消息。不能换 key 自动重发，也不能把所有 conflict 自动当成功。不同正文重用同 key 尚未测试。

一次临时探针只解析 stdout，遇到业务错误时 JSON 解析失败；之后捕获了 exit、stdout、stderr，确认错误 JSON 位于 stderr。这是探针处理缺陷，不是额外的钉钉业务故障。后续脚本必须同时处理两个输出通道。

### 参数名称不保证原生消息形态

本版本 `chat message send --help` 明确说明 audio/video 是 file 的语义别名，本地 PNG/JPG 也按文件发送；已有 mediaId 可走 image，但本版本 CLI 不提供本地图片到 mediaId 上传。五项实发的消息详情均返回 fileId 资源，历史以“[文件]”开头，与 Help 一致。

这证明当前路径的附件传输完整，不证明原生富媒体呈现。后续先验证较新官方版本是否提供真正的原生发送或资源上传入口；再决定是否需补充。不能将 v1.0.61 的行为扩大为钉钉平台永远不支持。

## 后续结果入口

本阶段提出的新版隔离、引用、分页、办公和服务实现已在后续执行，见 [首版实现](16-implementation-acceptance.md) 与 [新增验收](20-gap-acceptance-and-reproduction.md)。当前剩余工作仅以 [docs/13](13-roadmap-and-backlog.md) 为准，不重做本阶段发送。多人项目保持skipped_by_user。

## 可复用脚本

`scripts/solo_media_smoke.py` 固定目标配置、CLI 基线，逐项上传五种合成附件，查询 task 状态、下载并校验摘要。仅显式 `--execute` 执行；已有 intent/send 记录时拒绝重放，不自动重发未知结果。该脚本是实验工具，不是常驻 bridge；本轮已经执行，勿为查看结果再次发送，直接读 evidence。
