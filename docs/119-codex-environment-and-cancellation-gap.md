# Codex新环境已执行，但真实取消暴露迟到工具写入

2026-11-13，E118。**Codex普通执行与续接已有真实工具/文件证据，取消验收失败，因此尚未部署到IM私聊。** 群和私聊现仍为Kimi，产品仍87a3d39。不能再把Codex现状简写成“只有请求超时”，也不能因正常任务成功就称完整支持。

## 新的执行结果

同一Codex CLI 0.164.0及相同binary摘要，沿现有LocalRuntime契约和60秒期限，显式传入E115/E116已验证的runtime.environment网络配置；没有更改HOME、凭据、模型或用户配置。此次按OpenAI Docs技能读取[官方exec接口](https://learn.chatgpt.com/docs/developer-commands#codex-exec)。

| 新任务 | 实际结果 |
|---|---|
| E118初始 | 19.64秒，Python实际计算37×53=1961，JSON原件正确，可信turn.completed及退出0 |
| E118-R续接 | 17.02秒，同native session，Python读取上一文件并加7得到1968，新JSON正确 |
| E118-C取消 | 工具先写started标记，再sleep90秒；宿主约11.68秒返回cancelled，guard报cleanup_complete；但Python在started约90.007秒后仍写出late文件，约晚于取消返回89.827秒 |

[结构化证据](../evidence/2026-11-13/codex-persistent-env-and-migration-validation.json)明确`codexCancellationPassed=false`。初次立即检查时没有late文件，不能作为取消通过；延迟检查推翻了此前的口头判断。原失败产物、日志、时间与旧E105超时均留local，不删除、不重做同一个key。

网络环境改变后的两次成功说明当前条件可运行，未作完整网络因果对照，不能断言E105唯一病因。当前guard只处理其拥有的CLI进程组，`cleanup_complete`不能外推为所有执行器工具都已停止。本次真实进程归属未在取消前完整采样，不能凭late文件臆测确切PPID/PGID。

固定官方0.164.0源码提供了新的修复依据：`codex-rs/exec/src/lib.rs`在1192行监听ctrl_c，并在1313行向本turn发TurnInterrupt。已核tag及commit `6aaac694803004a63c6f393d153c96d22521a6b9`。[固定来源](https://github.com/openai/codex/blob/6aaac694803004a63c6f393d153c96d22521a6b9/codex-rs/exec/src/lib.rs#L1192)。下一候选应让Codex先走其原生中断、仍保留有限兜底及准确清理范围日志，先合成回归再新的真实取消验证。不能只给所有进程发更强信号或杀共享服务。

## 显式运行器切换工具

私聊通过veil UI发送一次`/agent new`，liev“已开始新会话”可见，原Kimi session/契约归档，88旧任务保持。随后只停私聊gateway、准备Codex配置，manager因原账本runtime binding不匹配而拒绝启动；没有Codex新任务投递。已恢复原Kimi配置和私聊gateway，群/transport原进程未动，两段维护写入原观察run。

该拒绝是正确保护，`new`只换会话代次，不应隐式解除执行器/会话绑定。新增[显式迁移工具](../scripts/migrate_agent_runtime_binding.py)：

1. 只接受同一路由、发送白名单和工具面，配置只能改变runtime部分。
2. 目标gateway必须由原manager确认停机；最后任务须为completed new，没有native session/contract、未终态任务或未确认outbox。
3. 先冻结配置/路由/完整任务账本摘要的local计划；执行时重核原计划，在SQLite事务内更新唯一binding并追加runtime_binding_history，其他任务/回执/元数据保持。
4. 不改配置、不启动服务、不执行模型/DWS。receipt先登记attempt；失败/未知不自动重试。配置由操作者在停机时准备，失败保持绑定不匹配的拒绝状态，不自动盖章。历史from/to身份只在local计划/数据库保存。

冻结源码及同一E115 wheel已安装Python3.14/3.11，各10方法通过。覆盖显式new、未决发送/任务、快照漂移、绑定不符、事务回滚、重复执行、配置范围、失配进程归属、CLI计划/回执；首次8项中的1路径规范化错误已修，原日志保留。产品21模块没变，没有重跑或宣称全量367项通过。该工具尚未对真实账本执行，Codex取消修复通过前不迁移现场。

## 当前下一步

先修复Codex原生中断及清理范围声明，至少覆盖直接取消、超时和宿主消失的合成路径，再用新的合成任务观察超过计划写入期限的真实无迟到文件证据。随后显式迁移私聊执行器、真实UI交办/续接/取消/下载打开；群维持Kimi。旧取消失败必须保留。当前49/14/1和7 MUST缺口不变，Kimi仍满足原至少一个执行器门槛。
