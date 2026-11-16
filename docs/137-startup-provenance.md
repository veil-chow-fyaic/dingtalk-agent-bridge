# 服务启动来源与实际观察准备

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->

E137，2026-11-16。用户明确要求接手全部后续闭环。原始需求是普通账号的群/私聊双向文字、多媒体文件和可替换Agent接入，办公作为扩展；保持原PRD/MUST，不把Kimi或四runtime全通过设为IM统一前置。

## 服务实际增加的能力

transport与gateway在ready时记录自身PID、Python版本、已导入模块来源、启动时24份产品源码摘要，以及自己实际读取并解析的配置字节摘要。manager在启动前取源码清单，在ready后核PID/入口/源码/配置，再把证据存进原进程归属记录。旧进程记录可正常停机，缺新证据时不能冒充版本验证成功。源码或配置不一致拒绝新启动并沿原归属回收，不迁移runtime/session。

这是启动来源及配置可追溯，不是OS认证或进程内存证明；不能保证恶意改文件后恢复或未采样瞬间无变化。观察器保存每次启动证据和进程身份，要求启动前、ready时和观察中源码/配置一致；维护或版本变化保留为失败。`uniform_startup_version_verified`有证据后可成立，`uniform_loaded_version_proven`仍不作内存级保证。

## 截止收尾修正

E136的5秒开始/15秒结束窗口对现场15秒历史轮询过窄：cut瞬间的watermark通常落后，不能靠一次立即快照证明覆盖。本轮在新run开始即写明30秒开始/45秒完成的收尾策略，固定cut不变；只读本地SQLite等待既有轮询覆盖，不主动触发DWS、停止服务或延长观察来掩盖失败。每次覆盖尝试的时间、水位、未完页和事件摘要保留，数据库错误立即终止。墙钟与单调时钟双重限时，时钟回拨不会无限等待。

无策略字段的旧v2仍用旧5/15容差，不更改旧run。更改预声明预算、缺尝试记录、未覆盖、迟到、版本/维护变化均不能通过。完整24h、零记录错误、统一启动来源组成有限范围的`stability_pass`；自然失效refresh和上游不丢消息始终另计。

## 验证与后续

[验证记录](../evidence/2026-11-16/startup-provenance-validation.json)：24产品模块/许可/六入口一致；冻结源码与同一wheel安装Python3.14.6、3.11.15各472方法通过（6新增启动来源、3新增收尾策略）。之后补单调时钟收尾边界，最终观察专项34方法在源/两安装环境各通过，不称473全量。产品字节未在后续专项中改变。

新来源测试包含真实合成子进程、两入口、摘要/来源/PID/配置篡改、旧记录无证明、manager保存/拒绝及混合模块来源。没有凭据、DWS或模型调用。准备按原维护门部署后，以新run-id做短采集闭环，再进入真实24h；本实现提交本身不计部署或观察。

[官方文档补读](../evidence/2026-11-16/official-media-boundary-recheck.json)确认main仍是E129相同HEAD。此前未读到的[chat原子命令文档](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/4cc7767c70a874b189463ebfb07ad8a3c424389c/skills/mono/references/products/chat.md)明确audio/video仍是file兼容语义，不能据参数名升级为原生语音/视频。未换binary、重试旧UI或重做模型失败样本。
