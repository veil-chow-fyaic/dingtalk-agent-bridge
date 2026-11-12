# 公开参考项目：先采用已有 DWS 真人账号实现

2026-11-12，E092建立、E097更新。优先研究GitHub社区和钉钉官方的DWS通道；本地WeCom不作为当前选型/实现来源。默认DWS授权真人账号，bot项目只参考可独立移植的交互设计。用户最新要求深入CEO，已完成新版31文件来源核对和采用清单。

## 阅读入口

- [中间件架构与真人身份决策](../architecture/dingtalk-agent-middleware.md)
- [具体采用/改造清单](adoption-plan.md)
- [首项代码采用：排队文件的原定摘要校验](artifact-digest-adoption.md)
- [CEO源码深挖与C01–C06采用项](ceo-deep-dive.md) · [新版31文件固定来源](ceo-deep-dive-index.json)
- [四类 Agent 的官方接入面](../architecture/agent-integration-map.md)，属于通道选型之后的工作
- [固定版本及文件 SHA256](catalog.json)
- [现有验收矩阵](../../plans/completion/ACCEPTANCE_MATRIX.md)，不把参考项目的声明计入本项目通过项

## 优先级与实际用途

| 优先级 | 项目/固定版本 | 身份与范围 | 采用判断 |
|---|---|---|---|
| P0 官方底座 | [DWS](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/tree/63a7c4906c7dee10750011ea309b9eb78abb7eb0)，v1.0.67，Apache-2.0 | 普通账号认证、消息、资源、事件和办公 API | 官方实现直接调用；不自行重写认证/通讯协议；本机版本不自动升级 |
| P0 通道主体参照 | [Qwen Code DWS channel](https://github.com/QwenLM/qwen-code/tree/41a3b9f5a6bbaad3c9fa98f341d5ae453b0265a0/packages/channels/dws)，Apache-2.0 | 普通账号，群/私聊、事件/历史、引用、会话、回复队列 | 最贴近主线；优先评估抽出 DWS client/事件/路由逻辑，解开 Qwen 宿主依赖 |
| P0 任务/交付/执行器参照 | [CEO Agent Service新版深挖](https://github.com/callzhang/ceo-agent-service/tree/92e360ed1eb35f006afee738916cc9b735c1deb5)，MIT；E093采用仍固定bd3de36 | 真人账号工作流及另配bot；文件回执、发送事实、持久会话/契约、运行器能力/错误 | 已采用摘要门槛并部署；继续提取可拆通用机制和负例。管理者画像、OA/OKR、强制A/B审核及自动认证恢复不引入 |
| P2 私聊参照 | [dsh-dingtalk-self](https://github.com/MinEagle/dsh-dingtalk-self/tree/706283968d2606b68261f0f4adaf189b10e8e791)，MIT | DWS 本人私聊、工作区绑定、草稿/确认/自动模式、附件 | 可参考会话和代答标识；私聊定位不能补证群聊；忙时自动新会话、正文删减策略不直接沿用 |
| P2 读侧参照 | [dws-message-cache](https://github.com/kerrmoulton/dws-message-cache/tree/cbfde38c12ce559509ac9bd35371e5356e54bdbf)，未确认授权许可证 | DWS → 本地 SQLite/媒体缓存 → CLI/Skill；分页/水位/显式 ack | 读侧设计有价值，不是双向 channel；许可证未确认前只参考设计，不移入产品代码 |
| P3 候选观察 | [dsh-superagent-dws](https://github.com/Shuai-S/dsh-superagent-dws/tree/4f63160e10440396472ec00667365a5be78af5ac)，未确认授权许可证 | DWS 本人群/私聊事件、引用及图片下载 | README 明确真实事件字段/回复端到端待验；不按“功能已写”认定成熟。其自动安装/登录及全群事件模式不采用 |

“成熟”按维护来源、实际源码、契约/异常测试、可复用边界、发布与真实验证证据分别判断，不按 star 或 README 篇幅排名。Qwen 是 Qwen 项目官方实现，并非钉钉官方通道；CEO 等是社区项目。本轮检查源码及测试文件，没有运行第三方服务或把其测试报告当本项目验收。

## 次级参照，不改变真人账号路线

| 项目 | 参考内容 | 不采用的部分 |
|---|---|---|
| [OpenClaw Slack/Telegram](https://github.com/openclaw/openclaw/tree/7b303779c41f9b67ba4291f646ce447e01fad868/extensions) | 会话/线程归属、合并消息后第二层去重、分段与未知投递对账、附件与交互 | Slack/Telegram token、bot 身份、权限集合及网络协议 |
| [钉钉官方 OpenClaw connector](https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector/tree/88df00ee594072e9941ef3f71da90a37f3291ad3) / [soimy 插件](https://github.com/soimy/openclaw-channel-dingtalk/tree/63956bc8ed9c168045a671271abb2ee1530c123d) | DingTalk 展示、回复分发、平台特有格式 | bot 接收/凭据/sessionWebhook，不作为 DWS 真人账号后端 |
| [fireairforce/dws-codex-bridge](https://github.com/fireairforce/dws-codex-bridge/tree/60a0a649630c1cd17da38972b7c9356f952dcd9b) | 数字员工 + Codex App Server 的接法说明 | 指定群/数字员工身份；UNLICENSED，未复制实现代码 |
| 官方 Codex、Pi、Kimi、OpenClaw 接口资料 | 下一阶段 runtime adapter 的协议依据 | 不以 Agent 接口研究替代 DWS 通道选型 |

另已筛除 AI 表格插件、DWS 工具集合、无状态 MCP 包等：它们能让 Agent 调工具，但不提供完整的主动接收/会话/交付通道。Hermes 名为“official”的社区移植也仍是机器人 Stream 通道加 DWS 办公技能，不是本项目真人 DWS 路线。

## 本地整理方式

`docs/references/catalog.json` 是入 Git 的索引：仓库、不可变 commit、许可状态、每个文件的来源 URL/SHA256/字节数、用途与优先级。

实际参考源保存在 `local/references/<项目>/<commit>/`；这是有意选择的源码、测试、文档和许可证快照，**不是可直接启动的完整 checkout**。不安装依赖，不运行其登录、后台或测试脚本；没有复制账号、token、聊天和运行目录。

E092的13来源/69文件catalog保留历史范围；E097另建CEO新版31文件索引，不覆盖旧版SHA，也不把两个版本的数量冒称独立组件数。新版每文件同时核Git blob/字节数/SHA256，检查深度分别注明：完整短模块、关键接缝/测试或仅边界参考。没有把下载等同通读或执行通过。

DWS 官方源码快照来自此前固定的公开 commit，不改变已安装 binary。其余公开快照来自相同 commit 的 GitHub raw 文件；可按 catalog 的 URL 重新取得并核 SHA256。两份早先取到的本地 WeCom 快照已从活动 catalog 排除，仅在 local 保留历史，不作为本轮优先复用依据。

后续真正移植代码时，在同一提交保留原 LICENSE/NOTICE/版权头、记录源文件和 commit、列修改与依赖闭包，并跑对应契约测试。MIT/Apache 条件按原文件保留；未授权仓库仅作文档/设计参照，不把“GitHub 公开”当任意复制许可。
