# 变更记录

记录影响使用者的变化。源码中的包版本当前为 `0.1.0`，不表示已发布正式版本、存在远端 release 或通过全部验收。精确部署与证据见[当前总览](docs/102-user-requirements-and-roadmap.md)，完整历史见[证据账本](plans/completion/EVIDENCE.md)。

## Unreleased

### 项目许可与协作

- 主代码采用 MIT；原第三方声明保留。GitHub仓库为 `veil-chow-fyaic/dingtalk-agent-bridge`，版本仍为开发阶段。

### 已验证、待部署

- 配置助手 `select` 为同账号新增会话时继承已有图片上传 helper，避免新增路由原生图片在上传前失败；同步修正 `migrate` 离线、`select` 需只读 DWS 核对目标的帮助。候选已经源码与独立安装验证，当前运行产品尚未应用。[验证范围](docs/145-delivery-and-recovery-closeout.md)

### 文档

- 重整产品入口、首次运行路径、用户/维护/历史导航，以及贡献与安全说明；不改变产品代码或原验收判据。

## 0.1.0 — 当前开发版本

以下为已经实现或验证的开发里程碑，日期不是正式发布日期。

### 2026-11-17

- 私聊原生引用补齐 UI、history 和 consumer 证据；源关系保持，未触发额外任务。群/私聊引用双向已有真实验证。
- 恢复本机原生截图路径后，核对两路既有图文组合的完整文字、双图顺序、发送者与 AI 标识；逐图客户端保存仍失败，未扩大为完整组合验收。[阶段记录](docs/147-native-ui-recovery-and-dm-quote.md)

### 2026-11-16

- 历史同步失败或不完整时持续显示错误状态，避免重启或显式同步掩盖失败。
- 隔离损坏图片标记、单条附件缓存 I/O 与循环链接问题，允许后续合法消息继续消费。
- 增加绑定精确 Git 提交、验证记录和已测 wheel 的离线导出工具。[交付说明](docs/144-offline-release-export.md)
- 本机 HTTP 客户端统一直连并拒绝重定向，避免代理环境将本机接口请求转交其他地址。
- 提供单条文字＋有序 PNG/JPEG 的组合发送；API、官方原件和用户端可见层分别验收。当前部署产品为 `2b479a8`。[部署记录](docs/143-parallel-hardening.md)

### 更早的基础能力

- 独立 CLI、loopback HTTP API、持久 consumer；group/direct 多路由与显式身份。
- 持久发送回执、幂等、未知状态对账、原件缓存与摘要校验。
- 可选 gateway 的任务/session/outbox、发送人白名单、取消和恢复；Kimi/Codex/Pi 有各自真实验证范围，OpenClaw 尚缺真实模型验收。

历史失败、未证类型与仍未完成的长期/自然刷新判据保持在[验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md)。本记录不承诺任意格式、所有组织、所有模型或持续无错误运行。
