# 运行器终态与会话兼容性

2026-11-13，E104。落实CEO C03/C04，产品只改`agent_runtime.py`、`agent_gateway.py`；不引入CEO的业务模型、Pydantic依赖、自动切路由或重试。该检查点未重载真实服务；transport仍E102、gateway仍E099。没有新增UI通过格或第二运行器可用声明。

## 复现与修复

在E102冻结产品上运行4个真实合成CLI负例，4个均失败：Kimi续接接受另一session、Codex续接接受另一thread、Codex完成事件后exit7仍交付、复用旧run目录后读取旧response文件。旧失败日志保留在local/runtime-session-20261113。它们是本地合成证明，不是平台实际串会话事故。

新行为：

- 静态`runtime_manifest`声明text、工作区文件/图片、工具、resume/cancel、结构化结果。Codex有原生图片参数；Kimi图片通过任务工作区与工具读取。`health=unknown`，不因为配置存在便推断登录、模型或安装健康。
- 配置可声明`runtime.requiredCapabilities`，不支持的能力在启动CLI前拒绝；不会改用另一个runtime。现有kind仍只有Kimi/Codex；Pi/OpenClaw尚未实现。
- Kimi需要assistant字符串后出现有效的`session.resume_hint`；允许其已知的终态后驻留行为并清理本次拥有的进程。Codex需要明确`turn.completed`、session与输出，再确认CLI退出0。普通工具输出、进度、exit0都不能独立证明成功。
- 输入/返回session必须非空合法字符串，续接只能返回原ID，同一次运行不能改ID。错误ID不写入宿主meta。新session在可信session事件后可保存，即使随后结果无效，也保留已有执行线索。
- run目录必须新建成功；历史attempt、stdout和response不被截断或当新结果。非终态退出、异常退出、缺失结果、未知provider失败使用稳定错误code；不从“429/auth failed”等工具文字猜登录或容量故障。全部不授予自动重试权限。
- `RuntimeResultError`保留E099的严格text/files结构与ValueError兼容；取消、超时、父死亡和进程组清理仍用已有守护。Codex提前回收后不能再对已回收进程wait；新增和原有后代清理测试覆盖这一点。

示例（通用配置，不含测试组织）：

```json
{"runtime":{"kind":"kimi","binary":"/absolute/path/to/kimi","timeoutSeconds":600,
"requiredCapabilities":["text","workspace_files","resume","structured_result"]}}
```

## 会话兼容性与旧数据

每个执行任务冻结`jobs.runtime_context`：执行前session、代次、静态adapter/result契约、显式model、workspace任务契约和办公工具面。session与`meta.session_contract`在同一事务保存。deadline、普通任务文字、路由命令前缀不是会话协议变更；model、adapter契约或办公工具面改变则拒绝旧会话续接。

不兼容任务标为blocked，发生在工作区准备/工具运行前；原session、历史任务、回执和文件保持，任务不会自动再排队。其他运行中session错误标为failed，不能说工具一定没有发生。用户明确`/agent new`才换代次；旧session与契约写入`session_history/<generation>`，连损坏的旧契约原文也保留。之后仍须提交新的明确任务，blocked任务不会复活。

**无元数据的旧session不能自动盖章为兼容。** 升级旧部署需要先停空闲gateway、备份账本、核其实际旧配置及加载版本与已审查兼容ABI，再显式写入那个旧契约；没有这些证据就保持blocked，不能用“当前配置”替未知历史背书。本次只在合成库验证该迁移机制，真实会话尚未迁移。E086旧办公wrapper升级测试补充了显式审查步骤；其暂停拒绝、原文件/历史保留断言未删除。

当前指纹是宿主明确版本，不会自动执行CLI探测、读取凭据或散列所有runtime安装依赖；同路径CLI升级仍须单独核协议。普通提示文案更新不自动重置上下文；若改变工具/输出/续接语义，维护者必须改ABI。此机制不是OS沙箱，也不证明任意第三方执行器已兼容。

## 验证和当前边界

[冻结验证记录](../evidence/2026-11-13/runtime-session-contract-validation.json)包含旧4失败、新24方法、冻结源码及同wheel双Python全量结果、21模块与六入口、源码/测试/许可摘要对照。首次开发运行的329项中1失败/5错误原样留local：Codex二次wait清理错误已修复，办公启用用例补显式兼容审查；不把该次写为通过。

实际历史Kimi运行只读检查：保存session与最后resume_hint一致。没有重跑旧任务。CUA以正确bundle绑定钉钉连续两次报`failedToCreateImageDestination`，按loop guard停止，不用其他UI技术绕过；没有发送、重载或账号操作。UI仍需在工具恢复后验当前候选，不能以离线测试替代。

## 参考来源与采用边界

固定[CEO运行器契约](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/agent_runtime_contracts.py)、[会话选择](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/consumer_agent.py#L681)、[契约负例](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_consumer_session_prompt_fingerprint.py)。已核固定索引5份源码/测试摘要；本次实现与测试自写，采用静态能力与健康分开、明确终态、会话兼容性这些设计，不运行上游服务/测试，不复制其自动清空session策略。既有CEO MIT文件保持随包。
