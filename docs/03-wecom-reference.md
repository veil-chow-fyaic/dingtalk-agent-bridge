# wecom bridge 实现对照

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


本地参考：/Users/veil/Projects/wecom-bridge；remote 为 https://github.com/fyaic/wecom-bridge.git；检出分支 feat/warecheck-native-mentions；提交 1ee7f8c，日期 2026-09-09。此处描述本地检出，不宣称与远端 main 同步。

## 已核对模块

| 模块 | 设计价值 | 钉钉迁移判断 |
|---|---|---|
| src/wecom/ax/monitor.py | AXObserver + 轮询、未读重采样、突发补读 | 复用调度思想，重写钉钉解析 |
| src/wecom/ax/controller.py | 会话搜索、聚焦、发送和确认 | UI 结构与动作全部重新探测 |
| src/wecom/ax/background_media.py | 0.25 秒预算、单任务媒体 worker | 避免媒体 IO 阻塞文本监听 |
| src/wecom/outbound_delivery.py | SQLite 幂等、同内容合并、投递查询 | 官方与 AX 共用账本 |
| src/wecom/file_staging.py | 队列附件持久化 | 复用生命周期设计 |
| src/wecom/inbound_reconciler.py | 未确认消息、重投与疑似丢失 | 为官方静默丢事件增加对账 |
| src/wecom/conversation_identity.py | 会话名规范化 | 钉钉优先稳定 ID，显示名只作辅助 |
| docs/official-capability-split.md | 聊天 bridge、办公官方工具的分工 | 钉钉调整为官方优先 |

## 不能原样复制的假设

企微图片可能不暴露 AXImage，现有实现用高度缺口和截图补足；不能将该经验用于钉钉而不测。AXPress、回车、前台判断、CEF/Qt 行为、组织切换结构和搜索弹窗都是客户端特定行为。元素序号仅在当前观测有效。

历史惰性加载、系统消息消失、侧栏未读打开即清除，都需要钉钉现场验证。此前确认指定群系统消息、文本气泡和输入框可读；本轮另核对DWS多图内联显示、办公文件卡片及文件引用。尚未实现钉钉AX监听/发送backend。

## 投递语义需要强化

现有 controller 对 send_arrival_unconfirmed 记录异常但可能仍返回 True，以抑制调用方重复发送；崩溃遗留 in_progress 可重新执行，属于 at-least-once，并非严格 exactly-once。

新 bridge 保留避免重复发送的意图，但公开区分 submitted、confirmed、outcome_unknown。官方调用超时后不能立刻 AX 重发；先查任务和消息历史。不要将 GUI 本地气泡等同于对端已收到或已读。

## 后续代码边界

不修改原仓库。先实现独立 Adapter 接口与能力记录，再决定是否提取公共组件。媒体补全异步执行，不阻塞事件接收；AX 操作按同一桌面会话串行化，保护剪贴板和当前输入草稿。
