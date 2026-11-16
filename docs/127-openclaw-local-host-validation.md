# OpenClaw 本地 turn 宿主验证（E126）

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-15：在独立 local 目录构建官方固定 `41f2b981d240cab9e55b07cba991282a795317b5`，通过回环合成 provider 执行完整 `agent --local` CLI。文字、同 session 续接、跨状态目录隔离、实际 Python 文件、独占锁拒绝、原生取消、工具期限及两个终态边界已有证据。未注册 bridge 的 OpenClaw 支持，未调用真实模型、认证、Keychain 或钉钉，未迁移 binding 或更改现有服务。

[脱敏证据](../evidence/2026-11-15/openclaw-local-host-validation.json)、[36 个固定源文件摘要](references/openclaw-local-host-contract.json)、[完整入口验证工具](../scripts/probe_openclaw_local_host.py)、[离线复核工具](../scripts/review_openclaw_local_host.py)。E125 的 14 项纯函数检查仍为历史层次，本轮没有重复它，也没有运行上游全量或 bridge 396/401 全量。

## 构建与冻结

官方源码 archive 的 65,102 个原文件与构建目录逐字节相同；原参考目录不修改。按 packageManager 的 SHA512 核 pnpm 12.15.0，`install --frozen-lockfile --ignore-scripts` 完成，1753 条锁记录通过原供应链规则，未关闭冷却期或安全校验。显式执行官方 `build:runtime`，28,020 个 dist 文件的摘要清单只留 local。Node 26.3.1、Python 3.14.6；依赖只安装在 local，不是全局安装或服务部署。

第一次构建自动拾取外层 bridge 的 Git commit；保留原 build-info 后，以完整上游 `GIT_COMMIT` 重建，最终构建身份正确。构建的 UI 体积预算及 Node 安全补丁警告保留；退出码 0 仅是本轮构建成功，不等于 UI 性能或该 Node 版本适合生产网络。

## 完整入口结果

输入为 `agent --local --agent main --session-id <完整UUID> --json --message-file -`，不带 `--deliver`。不同 CLI 进程向同一 session 续接；一份新状态目录使用同一 UUID 时不带入旧上下文。当前官方 `agent exec` 每次新 UUID 的限制没有改变。

| 样本 | 完整 CLI 与可核事实 |
|---|---|
| first / resume | exit 0、meta.stopReason=stop、aborted=false；同一 UUID，第二次模型请求确含第一条用户输入及 assistant 输出 |
| tool | 官方 exec 实际执行 Python `29*17+6`，JSON 文件值 499，toolSummary 1 次/0 失败；不是只让合成模型报答案 |
| isolated | 相同 UUID、新 state/config，模型请求不含 first 的用户/assistant 历史 |
| contender | 首个工具运行时第二 CLI exit 1，明确拒绝独占状态冲突，未产生第二个模型请求 |
| cancel | 只向自有 CLI 发原生 SIGINT；exit 130、stdout 无完整 JSON；已捕 7 个自有进程全部退出，无强制清理，工具起点后约 28 秒无晚写 |
| deadline | 原生 2 秒 turn 期限；exit 1，timeoutPhase=tool_execution、error.kind=incomplete_turn、fallbackSafe=false，表示副作用结果不确定；7 个自有进程退出，约 13 秒后无晚写 |
| length | exit 0 但 meta.stopReason=length，并附部分结果提示。bridge 必须拒绝当成完整成功，不能只认 exit 0 |
| missing | 合成 OpenAI 流 finish_reason=null 后 `[DONE]`，完整 provider/宿主将其规范化为 stop。不能声称 bridge 能从最终 JSON 还原未暴露的原始供应商字段 |

JSON 为整个 `payloads` / `meta` 对象，不是 exec 的 `ok/status/final` 信封，也不是逐行事件流。后续薄适配应核 session 一致、exit 0、明确 stop、非 aborted、无 meta.error/未解决工具错误，再从终态 assistant 文本解通用 text/files 结果；不把 `livenessState=working` 当另一轮仍在执行，也不把缺取消 JSON 当取消失败。原生截止失败仍不可自动重跑工具。

## 隔离事实与保留失败

显式设置独立 `OPENCLAW_HOME`、`OPENCLAW_STATE_DIR`、`OPENCLAW_CONFIG_PATH`、`XDG_CACHE_HOME`、临时目录和全新随机 profile；不覆盖 HOME/CODEX_HOME、不继承父环境凭据。插件、shell 环境导入及消息投递关闭；模型只指向 127.0.0.1 合成服务，声明的 key 为固定合成字符串。

仅设置 OPENCLAW_HOME 不足：SQLite 暂存缓存另受 XDG_CACHE_HOME 控制；macOS App 的 `mac-control.token` 则按系统 HOME 与 profile 查找。早期 default-profile 工具执行被测试钩子在 open 之前阻止，未读取凭据。随后采用从未存在的随机 profile；读取保护只允许该 profile 的不存在路径，并在任何文件出现时仍拒绝打开；未创建外部 profile 目录。三次 login-shell PATH 探测也被保护钩子拒绝，实际工具使用明确 PATH 与非登录 shell。此保护是合成测试的读/启动防线，不是对恶意 native addon 或任意工具进程的 OS 沙箱证明，也不是任意生产配置均隔离的承诺。

其他失败全部保留：最初 Node permission 模式禁用 fsync，在取得状态锁及模型请求前退出；第一版工具 fixture 错用 timeout，官方要求 timeoutSeconds，未产生文件；下一次被凭据路径保护阻止后，fixture HTTP 断开引发本地重试，未重跑真实业务。修正后实际 Python、状态锁与取消结果分开记录。

冻结执行工具有 21 项检查，其中 20 通过，1 项聚合检查失败并 exit 1：把 8 次**已阻止**的父目录 build-info.json 元数据探测也算成凭据访问。原 result/failure 不改写。修正仅发生在离线分类，继续拒绝这些文件读取；[离线工具](../scripts/review_openclaw_local_host.py) 对原始 9 个 CLI 样本执行 24 检查全部通过。额外 5 个反例（凭据路径、其他文件、缺样本、错误退出码、晚写）均拒绝；空源/变更源两个负例在启动 CLI 前拒绝。未为这处聚合口径重复整个宿主实验，也不把冻结工具原 exit 1 改称 exit 0。

原始配置、HTTP 请求、完整 JSON、SQLite、子进程记录、构建日志、执行工具冻结版和哈希均在 `local/openclaw-host-20261115/`，不进入 Git 或交接包。

## 下一段与项目边界

证据足够进入薄适配设计和本地回归：整对象输出解析、完整 UUID/独占 state 与明确 profile/config、stdin 输入、原生 SIGINT 加有界清理，以及配置/binding 兼容性。合成宿主通过不直接宣称真实 OpenClaw 模型或钉钉 UI 通过；实际部署仍需原生 new、零未决及显式迁移，不只改配置。

21 个 bridge 产品模块仍逐字节等于 e7d82cc，最近真实 UI/部署仍 E123。AIC Kimi、原私聊 Pi 不变；原观察与 Qwen 样本不重复。49/14/1、7 个 MUST 缺口保持，四 runtime 全过不是新增门槛，最终交接未完成。
