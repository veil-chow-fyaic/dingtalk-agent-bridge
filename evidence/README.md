# 证据记录与使用范围

本目录保存脱敏、可复核的阶段证据。[EVIDENCE登记](../plans/completion/EVIDENCE.md)说明每个事件的等级、文件和限制；[当前总览](../docs/102-user-requirements-and-roadmap.md)决定现在的状态。目录日期、文件编号和E编号不是同一套序号。

每次实验证据使用新日期或run目录，原成功、失败、初审错误、维护和未知均保留，不能覆盖旧结果。只增加本轮明确的材料，不因新版本发布回写历史状态。handoff-manifest是当前公开文件摘要，更新它不等于重新执行其中的历史测试。

## 怎样解释证据

- 帮助/源码/参数契约只证明接口形状，不证明认证或后端可用。
- 模型工具执行、可信终态、持久投递confirmed、原生UI和客户端下载打开/SHA分别取证；HTTP202、exit0、running或released不能替代。
- E131 auditPassed证明群双图入站及模型失败的证据完整，taskSucceeded仍为false。Kimi订阅403不等于DWS凭据故障。
- 长期观察必须带实际时间、版本、维护、错误和截止账本；事后数据库不是历史截止快照，两个旧run不重置或重审。
- E127最终423×3与E128新增3专项×3分开，不能相加声称426全量；历史安装包按冻结版本核对，不与当前HEAD混比。

## 采集和隐私

早期2026-11-10的local-observations、new-org-onboarding和cli-baseline属于开通前后历史，不能当成今天的账号/组织/授权状态。`capture_local_baseline.py`包含可能触发官方凭据机制的命令，不再把它列作无副作用健康检查；本机禁止额外真实auth/login/doctor/Keychain诊断，详见[AGENTS](../AGENTS.md)。

只为具体尚未完成的动作获取必要证据，已过实验不重复。账号ID、凭据、原聊天/AX/截图、数据库、日志及下载件仅留local或私有工具记录；公开证据只保存版本、计数、合成内容、摘要和准确限制。提交前扫描暂存blob并核manifest，不整包分发local。

E132新增文档索引和历史正文保护，属于离线资料校验；不产生新的产品、模型、DWS、UI或长期健康通过项。全量资料见[文档索引](../docs/INDEX.md)。

E133新增独立composition候选及CLI/HTTP合成验证；用户授权的单次最小Kimi请求仍为403，未提供周限额证据。无真实DWS组合发送/客户端原件验收，不提升R07。详见[阶段结果](../docs/134-outbound-composition.md)。

E134已部署2467fe2，群/私聊各一次文字＋双PNG组合confirmed；history和官方下载四原件字节/SHA一致。34只读检查/5篡改负例不等同客户端验收，矩阵保持51/11/2，99任务/240 Agent outbox/session保持。见[部署/通道报告](../docs/135-composition-api-deployment.md)及[脱敏证据](2026-11-16/composition-api-validation.json)。

E146恢复原CUA截图路径并完成一次私聊原生引用UI/history/consumer，R04通过，当前52/10/2、剩R01/R06/R07/R13四MUST。E134两路组合完整图文/身份/AI标识补齐，但重复旧点击保存路径仍失败，未计客户端原件。见[报告](../docs/147-native-ui-recovery-and-dm-quote.md)和[脱敏证据](2026-11-17/native-ui-recovery-and-dm-quote.json)；旧段落保留各阶段范围。
