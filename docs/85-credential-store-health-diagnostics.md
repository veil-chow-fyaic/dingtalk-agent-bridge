# E068：凭据存储故障的脱敏健康诊断

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


E065现场故障经DWS.call丢成泛型BridgeError，`/v1/health`和bridge doctor只能报告同步失败。2026-11-12补充明确诊断，帮助定位到官方凭据存储层，不代替官方认证，也不自动修凭据。

只识别固定v1.0.67已捕获的组合：官方error对象的category为internal、整数code为51，message具有完整的macOS DEK读取失败前缀。单独退出51、任意keychain字样、不同类别/代码或未知形状不映射为该原因。标准化异常只携带`credential_store_unavailable`，不保存或转发官方原始message。原始真实失败写在stderr；直接按原stdout/stderr回放分类成功，新增官方调用为零。

每路health新增`poll_error_detail`，已知原因含固定code/component/action/message，未知或恢复后为null；原poll_error字段继续保留。轮询更新两字段和HTTP读取使用同一短锁，网络调用不持锁。doctor重新构造允许的固定字段，不透传health带来的任意文本或扩展字段。提示明确不证明token已过期或钥匙串锁定，不能据此让用户盲目解锁。

初始5个测试方法在旧版有1失败6错误；最终6方法覆盖真实合成CLI子进程、八类不应归类的响应、两路互不阻塞、错误变化/恢复清理、原水位不乱进、HTTP定时轮询自动恢复、doctor恶意附加字段不泄漏，以及发送失败保持unknown、同key再次调用和重启均不重发。HTTP恢复属于隔离合成测试，不是E065真实凭据恢复。

源码及两个新建Python3.14/3.11已安装wheel环境各207项通过，六入口/19模块摘要匹配，20项审计通过。测试与合成资料复制到安装测试目录，未放入产品源码或账号资料；E064构建器以公开integration文件参与测试，不冒称内置在runtime wheel。

本次还修正E063/E064只读审计再次用当前源码核旧实验的问题：分别核既有冻结源码/旧安装模块，`currentProductMatchesFrozen:false`单独呈现。原共享报告摘要不变，两个冻结模块摘要篡改负向均被拒绝。首版错误与复核输出留local。

**新源码和wheel尚未加载到现场三个进程。** 原进程、官方binary、补充binary、配置、两路任务/投递/会话/日志及原观察保持；E065真实Keychain错误仍在。为保留用户普通终端对照及原进程自动恢复证据，不在故障中重启来展示新字段。恢复后再按既有manager归属和空闲条件加载，届时另记录维护和部署证据。

证据：[安装](../evidence/2026-11-12/credential-health-install.json)、[20项审计](../evidence/2026-11-12/credential-health-validation.json)；复核`PYTHONPATH=. python3 scripts/accept_credential_health.py`。原始文件在`local/credential-health-20261112`。没有新UI发送、账户授权修改、失效refresh恢复或24h通过结论。
