# DWS新增提交与剩余消息入口复核

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-15，E129。完成E128父进程死亡/new链路后，转回剩余MUST，仅读取公开官方增量；没有真实DWS调用、升级、UI操作或凭据访问。

[官方main](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/commit/4cc7767c70a874b189463ebfb07ad8a3c424389c)已到`4cc7767c`；[相对E122固定c4be030e的完整比较](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/compare/c4be030ea0470457faea167760613372d761fc5c...4cc7767c70a874b189463ebfb07ad8a3c424389c)返回全部14个提交、23个变更文件。稳定release仍[v1.0.68](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.68)，main有v1.0.69-beta.1发布记录，未安装。

这批业务增量属于[VoIP邀请事件的MeetingSDK字段](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/4cc7767c70a874b189463ebfb07ad8a3c424389c/skills/multi/dingtalk-event/references/event-voip.md)和[个人通话纪要自动开启设置](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/4cc7767c70a874b189463ebfb07ad8a3c424389c/skills/multi/dingtalk-misc/references/voip.md)。其余为发布、测试和CI。变更清单没有chat消息实现/文档，也没有连接阶段诊断变更。依据这一限定增量，没有发现可用于原生语音消息、独立video、引用或多附件的新入口；不能把VoIP通话能力算入IM消息验收，也不外推所有第三方项目均不存在实现。

内置网页工具未能打开两个GitHub API地址，之后无认证公开HTTP成功获取main、release和完整compare。固定main的chat原文HTTP请求25.01秒超时、0字节，未重试；没有将这次失败写成“已读最新chat全文”，结论来自完整差异清单及其中的官方文档补丁。

[脱敏证据](../evidence/2026-11-15/dws-entry-delta-review.json)保存提交/文件库存、固定源链接、原始响应摘要和失败范围；完整公开响应只存`local/dws-entry-review-20261115`。当前产品候选500191a、真实部署E123/e7d82cc、49/14/1及7项MUST判定均不变。

本入口检查已完成。下一次只有新的官方协议/UI入口或新的连接细阶段证据才进入对应实验；无变化不重复此diff、旧UI、原观察、Qwen或E128宿主样本。最终封版仍受原MUST与自检约束，不用补充的离线测试替代缺失的真实验收。
