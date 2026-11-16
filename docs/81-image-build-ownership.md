# E064：图片补充独立构建与覆盖保护

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12。可选图片上传构建器原先直接把Go产物写到`--output`，没有检查现有文件归属；回执还无条件写`stockDWSUnchanged:true`。即使运行中的官方DWS实际未被触碰，这也不是可靠的交付约束。

使用合成Git响应和真实子进程假Go复现：旧脚本把占位的“官方二进制”覆盖为补充产物，4个新测试方法出现3失败、1错误。没有用真实官方二进制进行破坏实验。修复在修改源码或运行Go之前拒绝无有效回执的现有输出、摘要已变化输出、符号链接/非普通文件、非预期生成测试文件。合法旧回执兼容；新回执增加测试源码摘要和是否替换已验证产物，删除无条件的官方二进制保持声明。

4个新方法覆盖首次构建、合法重建、未知/被篡改产物、坏回执、符号链接和测试源码保护。源码全量及Python3.14/3.11两个既有已安装runtime各201项通过；安装测试目录另外复制了公开的构建器，它不属于runtime wheel。诊断在测试清理前保留。19个runtime模块、现场补充入口及三份配置没有修改或重载。

独立构建先尝试官方远程克隆，网络超时退出128，保留原日志；随后仅从已验证的官方Git对象创建独立checkout，没有复制原工作树、账号或配置。上游固定commit为`63a7c4906c7dee10750011ea309b9eb78abb7eb0`，构建前干净。使用已有Go1.26.7、`GOPROXY=off`、`GOSUMDB=off`及`GOTOOLCHAIN=local`和缓存依赖，真实通过上传函数6子用例、2个命令/schema完整性测试和Go编译。工作树只变化一行注册以及两个补充Go文件。

新产物的帮助及无账号dry-run成功，计划为CHAT_IMAGE、未执行上传、未压缩。隔离DWS配置目录由程序生成了`logs/dws.log`，因此原记录`emptyDwsConfig:false`保留，不能称目录始终为空。新旧补充二进制摘要不同；没有承诺逐字节可复现，也没有部署新产物。原版DWS、现场补充、配置实际摘要在前后及审计时保持相同。

22项只读审计见[image-build-validation.json](../evidence/2026-11-12/image-build-validation.json)，复核入口为`PYTHONPATH=. python3 scripts/accept_image_build.py`。原始日志/独立checkout/安装测试目录只在`local/image-build-20261112`。不覆盖恶意并发改写、OS沙箱、全新机器离线准备或新UI。E063交接包仍固定旧提交82e1c2a，包含旧构建脚本；最终交付必须重新导出当前提交，不能把它当最新包。

构建期间现场出现独立真实同步失败，审计明确输出`transportHealthyAfterBuild:false`。没有发送新消息，也未修改授权。故障及恢复要求见[docs/82](82-live-keychain-read-failure.md)；审计通过只说明上述证据成立，不代表服务健康。
