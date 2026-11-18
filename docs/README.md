# 文档导航

第一次使用从[上手指南](getting-started.md)开始。需要判断是否满足自己的场景，先读[能力、当前状态与剩余工作](102-user-requirements-and-roadmap.md)。产品与部署状态以该总览为准，历史报告保留其当时结论。

## 使用与集成

| 你要做什么 | 阅读入口 |
|---|---|
| 安装并接通一个会话 | [上手指南](getting-started.md) · [身份、组织开通与接入经验](11-onboarding-lessons.md) |
| 使用CLI、HTTP或独立consumer | [接口参考](22-generic-tool-and-consumer.md) · [OpenAPI](../api/openapi.json) · [路由模板](../config.routes.example.json) |
| 接入已有运行器 | [实际支持与验证范围](architecture/agent-integration-map.md) · [运行器中立接入边界](21-existing-runtime-integration.md) · [配置模板](../config.agent.example.json) |
| 收取语音或保存组合原图 | [实测与客户端操作](151-native-voice-and-image-saving.md) |
| 处理图片 | [图片上传补充的构建与边界](../integrations/dws_image_upload/README.md) |
| 安全运行 | [安全说明](../SECURITY.md) · [运行手册](15-service-runbook.md) |
| 获取离线包 | [精确源码与已测wheel导出/安装](144-offline-release-export.md) |

## 维护与开发

| 你要做什么 | 阅读入口 |
|---|---|
| 启停、恢复、迁移与回滚 | [运行手册](15-service-runbook.md) · [风险与关闭条件](114-dws-risks-and-resolution.md) |
| 理解组件分工 | [中间件架构](architecture/dingtalk-agent-middleware.md) · [官方/社区参考](references/README.md) · [采用清单](references/adoption-plan.md) |
| 提交代码或文档 | [贡献指南](../CONTRIBUTING.md) · [变更记录](../CHANGELOG.md) · [仓库约定](../AGENTS.md) |
| 继续当前工作 | [当前任务](../plans/completion/CURRENT_MISSION.md) · [关键路径](../plans/completion/CRITICAL_PATH.md) · [TODO](../plans/completion/TODO.md) · [HANDOFF](../plans/completion/HANDOFF.md) |
| 核验需求与完成条件 | [计划入口](../plans/completion/00-README.md) · [PRD](../plans/completion/01-PRD.md) · [验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md) · [最终自检](../plans/completion/10-自检清单.md) |
| 检查资料和提交 | [文档检查](../scripts/review_documentation.py) · [覆盖声明检查](../scripts/review_acceptance.py) · [handoff检查](../scripts/verify_handoff.py) · [测试入口](../scripts/run_tests_with_evidence.py) |

部署 commit、已测 wheel、文档 HEAD 和候选补丁分别记录；后来的文档提交不证明服务已升级。检查脚本只证明其对应的资料/测试范围，不能代替真实消息、客户端下载或长期运行验收。

## 历史与证据

[完整索引](INDEX.md)收录全部资料；[索引数据](documentation-index.json)标明现行说明、固定参考、阶段历史、验收基线、累计账本与冻结归档。[证据登记](../plans/completion/EVIDENCE.md)、[推进账本](../plans/completion/PROGRESS_LEDGER.md)和[执行偏差日志](../plans/completion/99-执行偏差日志.md)用于逐项追溯。

编号不等于证据ID，例如文档132对应证据E131。阶段报告页首有历史范围，其“当前、暂停、下一步”按当时解释；旧失败、原判据和归档不回写成后续成功。继续操作先回到当前任务和运行手册。

<details>
<summary>常用历史检查点与研究入口</summary>

| 主题 | 保留的记录 |
|---|---|
| 公开仓库与CI | [公开MIT、启动修复、安装验证与分支保护](149-github-public-launch-and-ci.md) |
| 部署检查点 | [E150 实际部署](150-native-voice-and-acceptance-scope.md) · [E143 可靠性修复](143-parallel-hardening.md) |
| 私聊原生引用及早期组合操作 | [UI恢复、私聊引用及组合保存边界](147-native-ui-recovery-and-dm-quote.md) |
| 图文组合 | [组合API/部署及官方原件](135-composition-api-deployment.md) |
| 引用与模型失败 | [群引用双向](131-group-quote-ui.md) · [群双图与Kimi拒绝](132-group-multi-image-and-provider-denial.md) |
| Pi实际任务 | [历史部署与UI](124-pi-deployment-and-ui.md) |
| OpenClaw | [薄适配](128-openclaw-adapter.md) · [父进程死亡与恢复](129-openclaw-gateway-lifecycle.md) |
| 官方取消候选 | [早期双层候选](117-dws-cancellation-candidate.md) · [完整集成及边界](146-dws-root-cause-and-integration.md) |
| 观察记录 | [旧观察收尾](125-observation-closeout-and-qwen-transactions.md) |
| 参考研究 | [CEO深挖](references/ceo-deep-dive.md) |

</details>

后续任务与逐项关闭条件见[交付路线图](ROADMAP.md)，原活动清单与验收判据保留，避免按历史阶段重复建任务。

[E150 部署与测试](150-native-voice-and-acceptance-scope.md)记录 533 项源码及同 wheel 双安装验证。[E151 媒体实测](151-native-voice-and-image-saving.md)记录真实语音入站、出站转发结果和四张原图的客户端保存方法。
