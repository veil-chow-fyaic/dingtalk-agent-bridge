# E094：DWS 底座故障分层与本机直接证据

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


> 当前结论以[E113风险与解决状态](114-dws-risks-and-resolution.md)为准；本页是E094历史诊断，以下停机/待许可/未部署步骤不是当前指令。E112已恢复两路并真实UI验收，但系统故障根因仍未确认。

2026-11-12。用户要求先解决反复调用所依赖的 DWS 底座。当前结论：**已定位事故起点所在的系统层，并复现官方超时缺口；尚未证明认证已根治。** 本轮没有真实 DWS、auth、doctor、Keychain 访问或服务恢复。只读公开源码、已有事故记录及故障时段系统日志，并运行合成子进程；原始系统日志留在 local。

## 本机系统日志补齐了什么

[脱敏证据](../evidence/2026-11-12/dws-base-failure-diagnosis.json)记录只读日志查询范围与原件摘要。时区为 Asia/Shanghai：

| 时间 | 已观察事实 |
|---|---|
| 09:25:14.616960 | Computer Use 的 CUALockScreenGuardian 出现连接事件 |
| 09:25:18、09:25:19 | 原事故账本中群、私聊最后成功同步，见 docs/82 |
| 09:25:20.816139、.816147 | loginwindow 写凭证路径出现两次 invalid param(s) |
| 09:25:20.816152 | loginwindow 记录使用密码解锁屏幕成功，随后尝试解锁登录钥匙串 |
| 09:25:20.968420 | loginwindow 明确记录无法从屏幕解锁流程解锁钥匙串，SecKeychainLogin 返回 -25293 |

这次有系统日志中的完整 OSStatus，不是把 DWS 的八位 exit51 反推为唯一错误码。证据将事故起点定位到 **系统登录钥匙串解锁失败**；它发生在钉钉 API 之前，解释了为什么普通终端与后台都无法读取 DWS 登录密钥。

公开的 [OpenAI issue #60687](https://github.com/openai/codex/issues/60687)于 11 月 10 日创建，报告 macOS 26.5.1 上 Computer Use 活跃时，密码解锁屏幕后出现同样的 loginwindow/invalid param/-25293 特征。本机系统版本亦为 26.5.1，本轮日志高度吻合。**该 issue 仍为用户报告，本次未取得官方确认的因果或修复版本；不能断言 CUALockScreenGuardian 已被最终定责。** 原因归属仍需维护者确认或安全的受控对照。没有执行评论建议的注销、重启、停系统守护或锁屏实验。

## 三层问题不能混成一个“DWS 坏了”

| 层 | 已证事实 | 修复责任与未证部分 |
|---|---|---|
| macOS / Computer Use 环境 | 屏幕解锁成功后，系统登录钥匙串解锁失败；普通终端也读不到 DWS 密钥 | 不能归咎于用户密码输错、钉钉权限或单纯 Codex 沙盒；Computer Use 因果与持久修复未证 |
| 官方 DWS 与依赖 | 未分类密钥读取失败时拒绝覆盖旧登录；钥匙串等待超时不取消底层操作 | 拒绝覆盖是保护行为；超时取消与错误可观测性存在可复现缺口，需要上游补强或外层约束 |
| 我们的 bridge 和事故处置 | 当时后台重试未先隔离，又安排钥匙串锁定/解锁，放大弹窗影响 | 这是我们处理不当。E072/E073 已补持久暂停、调用限流和归属清理，但尚未部署，也不能修复系统解锁故障 |

[官方 PR #1430](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/pull/1430)允许确定的缺密钥/密文不匹配在取得新登录后定向修复；对未分类的 Keychain 读取故障仍拒绝覆盖。这解释用户的 auth login 在新授权之前被拦住，不是 token 过期或 OAuth 失败的证明。[#214](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/214)讨论沙盒兼容，但普通终端同样失败的事实使它不能单独解释本机事故。保留系统钥匙串模式，不用 file-DEK 或 reset 掩盖故障。

## 新复现：官方的五秒超时不是底层操作取消

固定官方 v1.0.67 / 63a7c4906c7dee10750011ea309b9eb78abb7eb0。检查 [Darwin 实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/keychain/keychain_darwin.go)与 [go-keyring v0.2.8](https://github.com/zalando/go-keyring/blob/v0.2.8/keyring_darwin.go)：

- worker 的 context 只供外层 select 等待；超时返回后没有取消实际读取。
- go-keyring 使用不带 context 的 exec.Command 启动系统读取。失败时除 NotFound 分类外没有保留 CombinedOutput，限制诊断信息。
- default-keychain 预检查在 worker 的超时范围之外。这是静态源码结论，本轮未运行系统命令来复现该路径。
- 新 [独立 Go 复现](../evidence/2026-11-12/dws-keychain-timeout-probe_test.go)按原字节提取 worker，仅用合成子进程替代读取，把等待缩为 30ms。超时已返回时，合成子进程仍存活、worker.done 未关闭；最后仅清理自己创建的合成进程并等待回收。正常完成对照通过。共 2 项通过、1 个 helper 跳过，这是**缺陷复现成功**，不是上游修复通过。
- probe 使用本地错误包装 stub，未链接官方 Keychain 包或运行其 TestMain，不运行真实 DWS 或 security；[Apache-2.0 许可](../evidence/2026-11-12/dws-keychain-timeout-probe.LICENSE)随摘录保留。
- 当前 [v1.0.68](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.68) 的该 Darwin 源文件仍与 v1.0.67 同字节，没有取得通过升级修复本次问题的证据。

这能解释读取等待积累的风险，并支持已有 bridge 进程防护；**不能据此断言官方超时缺口触发了最初的系统 -25293，也不能承诺外层清理能撤销所有已经交给系统 UI 的授权请求。** 普通终端直接运行 dws 不经过 bridge 的防护。

## “解决好”的验收顺序

先暂停新增 channel/runtime 功能，把底座稳定性列为当前 P0；Qwen 接纳边界研究后移。不是换 bot，也不是重新实现认证。

1. 保持当前停机与系统钥匙串模式，固定官方 binary/profile/环境；不重放两个已消耗的查询记录，不修改凭据或做锁屏、解锁、重启实验。本轮已完成系统日志定位与官方缺口复现，不重复取同一时段日志凑进展。
2. 新真实核验需单独明确允许，范围应先是前台、单路串行、固定总次数和时间、首个失败立即停的业务读取；不启动后台、不自动 login/doctor、不并发请求密码。现有 E090 是后台恢复方案，不能代替这个底座判断；也不再为此堆审批工具。
3. 读取稳定后，才讨论受管私聊 transport 的限时补读，停机核账本，再开放 Agent；自然 access token 轮换、后续同步和故障停止分别留证。不得人为改 token/时钟造故障，不以成功调用数量代替 UI 验收。
4. 如果系统解锁失败复发，外层熔断只能止损；需核官方 Computer Use/macOS 修复，或另行设计执行环境隔离。同机换终端不能隔离系统登录钥匙串。不能通过放宽密钥保护、绕过系统限制或重试把错误“跑没”。

历史上 E028 确有一次自然预刷新及跨旧到期时间同步，不能说从未测过刷新；但它发生在事故前。事故后 E089 只有一次现有凭据业务读取成功，auth login 尚未重测，持续调用与系统故障不复发都未验收。当前没有依据承诺其他设备永不复发，也没有依据把问题归结为 DWS 无法支持普通账号 IM。

本轮不改产品模块，不重跑 291 项旧全量，不改变 MUST/UI 矩阵，不恢复服务或心跳；新诊断与后续重点写入同一项目账本。

## E095 后续状态（覆盖本页当时的待许可/停机）

用户已在新终端完成登录并提供liev成功截图，要求回主线；又明确新AIC测试群可继续，企业大群禁测。E095按新授权、新群与E093产品实际恢复history双路并完成群/私聊文件UI，见[记录](100-aic-group-resume-and-files.md)。旧E090的E084冻结提案不宣称被原样执行，旧两次query key仍保留不重放；E094诊断不被写成因果根治。系统Keychain/auth诊断等仍禁止。
