# E091：回到 IM channel 主线、DWS 边界与现成实现

2026-11-12。用户对 E090 的回复是在追问产品方向、群聊覆盖、登录故障和现成项目，**不是恢复许可**。本次仅核已有证据和公开一手资料；没有真实 DWS、认证、后台或 UI 操作，没有新增通过格子。E090 保留为未执行提案，不重复催问，也不再为等待许可新增恢复审批工具。

## 主线和交付边界

目标是：用户从钉钉私聊或群聊交办，普通账号通道把文字和附件送到本地可替换 Agent，Agent 真正执行任务，将说明和可下载原件交回原会话，并在重启、断线或发送结果未知时保留准确状态。当前 liev 是 DWS 授权的普通账号，veil 是真人测试用户；没有创建 bot。Kimi 已有真实工具与文件交付证据，Codex 可选适配不能反过来阻塞任选一个执行器的要求。

| 层 | 应由谁负责 | 本项目状态/必要补充 |
|---|---|---|
| 账号授权、profile、token、钉钉权限 | 官方 DWS | 不自研登录、不保存第二份 token；当前认证持久可用性仍未验收 |
| 消息发送/回复/历史/事件、资源及办公 API | 官方 DWS | 普通账号群/私聊基础链路已经真实验证；继续沿用官方参数和能力，不重写 IM 协议 |
| 通道策略 | bridge/channel | 统一消息、固定身份与白名单、群触发规则、自身消息过滤、引用/附件关联；已有实现，剩余按矩阵验收 |
| 本地执行 | 可替换 runtime 适配器 | 会话、任务状态/取消/超时、真实工具；Kimi 已通，CLI/HTTP/consumer 不绑定某个模型 |
| 可靠交付 | bridge 调用官方回执能力 | 持久 inbox/outbox、去重、补读、发送结果未知时按原 key 对账、原件校验、同会话回传；已有实现，停机修复尚未部署 |
| 已证官方缺口 | 狭窄补充 | 固定 v1.0.67 本地独立 CHAT_IMAGE 上传补充复用官方鉴权/上传；不把它扩大成所有 DWS 图片能力都不存在 |

结论：DWS 足以作为本项目的通讯底座，已有真实收发和第三方 channel 实现支撑这个判断；**不等于 DWS 裸命令已经完成通用 Agent channel，更不等于当前项目已达到全部验收**。新增代码必须对应一个明确的产品缺口，不能以测试/审计工具数量代替通道可用性。

## 已有 channel：身份、复用价值和限制

| 实现 | 身份/宿主 | 已核能力 | 对本项目的决定 |
|---|---|---|---|
| [Qwen Code DWS channel](https://github.com/QwenLM/qwen-code/blob/41a3b9f5a6bbaad3c9fa98f341d5ae453b0265a0/docs/users/features/channels/dws.md) | DWS 已登录普通账号；Qwen Code | 私聊/群聊、独立启停策略、Stream 与历史补读、会话、去重、持久回复队列、引用 | 最贴近当前身份的主要参考；保留 runtime 通用性，不要求用户改用 Qwen |
| [DWS 内置 dev connect](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli#dingtalk-bot--connect-a-robot-to-your-local-ai) | 钉钉机器人；本地 Codex/Claude 等或 agent-cmd | 群内 @、本地 CLI、多轮会话及 new/clear | 官方已有更短的 bot 接入路线；身份不同，本轮不建 bot、不替换普通账号方案 |
| [钉钉官方 OpenClaw connector](https://github.com/DingTalk-Real-AI/dingtalk-openclaw-connector) | 钉钉机器人；OpenClaw | 群/私聊、卡片、多 Agent、附件 | 是官方 channel 插件，DWS 办公技能与机器人消息通道分开；不当作普通账号 DWS 通道已验收 |
| [fireairforce/dws-codex-bridge](https://github.com/fireairforce/dws-codex-bridge/blob/60a0a649630c1cd17da38972b7c9356f952dcd9b/README.md) | DWS 数字员工；指定群/主管；Codex App Server | 多轮线程、进度/结果卡片、图片输入输出和回执 | 可参考 Codex App Server 接法；不是当前普通账号群/私聊全覆盖替代品。README 明确 UNLICENSED，不直接复制代码；其本地测试也明确不证明真实钉钉 UI |
| [openclaw-dingtalk-auto-reply](https://github.com/cuyua9/openclaw-dingtalk-auto-reply) | DWS 普通账号私聊；OpenClaw | 私聊历史、session/transcript 映射和自动回复 | 是另一条真实存在的个人账号路线；主要目标是私聊风格回复，不能据 README 认定覆盖群文件任务矩阵 |

另有 [dingtalk-workspace-mcp](https://github.com/sputnicyoji/dingtalk-workspace)：把 DWS 命令暴露为 MCP tools，认证仍委托 DWS；它自述无状态协议适配，不承担主动消息接收、任务调度和持久交付，不能把“接入 MCP 工具”当“完成 IM channel”。上述社区能力是文档/源码核对，本轮未安装或运行其程序。

### Qwen 源码对照后的保留项

本次固定 Qwen commit `41a3b9f5a6bbaad3c9fa98f341d5ae453b0265a0`，复核文档、[channel 源码](https://github.com/QwenLM/qwen-code/blob/41a3b9f5a6bbaad3c9fa98f341d5ae453b0265a0/packages/channels/dws/src/dws-channel.ts)、[client 源码](https://github.com/QwenLM/qwen-code/blob/41a3b9f5a6bbaad3c9fa98f341d5ae453b0265a0/packages/channels/dws/src/dws-client.ts)及 Apache-2.0 LICENSE 与本次读取的 main 字节相同。

- 值得对照复用的设计：profile 固定、self 身份过滤、群/私聊独立策略、事件与补读去重、会话分离、回复持久化和原 UUID 复用。这些在本项目多数已有实现，不为换框架推倒重做。
- 已核 client 的 IM 输入契约为 content/referencedText，发送方法调用 text；没有看到与本项目等价的附件原件输入/输出契约。不能据此断言整个 Qwen runtime 完全无法处理文件，但它没有直接证明我们的各格式四方向交付要求已满足。
- 它的回复队列满 100 时丢最旧项，超 12000 code points 截断；当前源码在发送前 checkpoint 失败后仍尝试发送。这些取舍与本项目保留失败/未知记录、完整文件交付的要求不同，不原样移植。
- client 的 execFile 超时与 child.kill 针对直接子进程；仅这些代码不能证明覆盖本次 macOS security 后代进程及共享 Setsid bus 的问题。不能用换 channel 代替认证故障与进程边界验证。

当前决定是保留已工作的通用 bridge，并把 Qwen 作为普通账号通道的主要设计基准；DWS 内置 bot 路线作为清楚列明的替代方案。尚无证据表明整包替换更省事或能免除本项目剩余验收。

## 群聊：测过，但没有测完

按现有 [验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)和原始证据登记，群/私聊基础收发、真人 UI 任务，以及 PDF/DOCX/XLSX/ZIP 四方向和群 PNG 入站已取得历史证据。群普通消息只接收不执行、自身回复过滤也有验证。它们并非本轮新测试，也不等于事故后新版本已部署。

群剩余：TXT 独立入站、CSV 双向、PNG 出站原件下载打开、JPEG/WAV/MP4、长文与引用、status/cancel/new、部分多附件，以及 E070 显式文件关联的部署和真实 UI。WAV/MP4 作为文件与原生语音条/独立 video 分开。当前多人实测按最新工作区指令暂跳过；不因此把群验收降级或改为通过。

私聊已验证的范围更广，包括常用附件、图片、WAV/MP4 文件、真实 Kimi 任务、上下文和控制。入站引用、部分附件组合、原生媒体与停机后恢复/持续运行仍有缺口。原观察的故障和维护不删除、不重置为“健康 24h”。

## auth login 是否解决、为何重登也失败

**尚不能称 auth login 已解决。** E089 只证明现有凭据支持一次指定会话查询：exit0、目标匹配。没有重跑登录，未验证长期刷新、后台持续工作，也没有获得系统问题已根治的证据。

已确认的故障链：macOS Keychain 中的 DEK 读取失败（security exit 51），导致旧 auth-token 无法安全解密/读取；DWS 拒绝覆盖可能唯一的旧登录态，因此登录在进入新授权之前被拦住。这不是已经证明的 token 过期。用户普通终端也失败，所以不能只归因 Codex 沙箱。

[官方 README](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli#authentication)和 [PR #1430](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/pull/1430)区分了确定的缺 DEK/密文不匹配，与暂时或未分类的 Keychain 读取错误：前者可以等新授权后定向修复，后者仍拒绝覆盖。这个机制解释了“重新登录也被拦”，但不是本机 exit 51 的底层根因报告。本次核到最新发布为 [v1.0.68](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.68)，没有取得它能修复本次故障的证据，不升级试运气。

底层究竟是系统安全服务、条目访问状态还是其他暂态故障，目前无法确定。弹窗事故中，桥接的后台读取/重试未先隔离，我又安排了钥匙串 lock/unlock，放大了用户桌面的影响；这是执行处理错误，不要求用户为此反复输入密码。已加入的暂停、限并发、超时清理和受管入口降低桥接放大故障的风险，不宣称修改了 macOS 或 DWS 认证根因。

其他设备可复用源码、配置结构和适配器，不能把本机登录态当跨设备通用文件复制。官方分别使用 macOS Keychain、Linux 文件密钥和 Windows DPAPI 等存储机制；官方 Linux 导入导出也不等于 Windows 的 DPAPI 可以直接迁移。未来每个目标设备应使用官方登录并验证业务读取、刷新和真实收发；尚未跨设备实测，不能保证不会复发。用户要求保留本机系统钥匙串模式，继续遵守。

## 后续顺序

1. 本轮完成方向与复用边界澄清，固定一手资料；不以 E090 回复作为允许启动。保留现成可用通用层，不增加新的审批/巡检脚本。
2. 独立代码工作只针对矩阵中具体缺口，并先对照官方或 Qwen 的实际契约；不得重跑已过实验凑进展。Codex App Server 是可选适配参考，不替代已满足的 Kimi 门槛。
3. 后台明确获准后才按既有 E090 提案恢复私聊补读、停机核账，再验证真实任务/附件和故障停止；不是先开启全部轮询再修登录。认证长期可用性与 auth login 仍单独列未证，不自动重登。
4. 群范围重新允许后补群矩阵；原生媒体/引用若没有明确入口则保留具体限制。完成真实稳定性、错误处理和最终交接后再验收项目。

本次修改仅为资料与计划纠偏，不改变产品、PRD、验收标准、已消费的两次查询记录或 E090 冻结提案。定时任务当前为 PAUSED，更新续作内容时保持原状态，不自行启用。
