# 钉钉 bridge 当前接手入口

E149已公开[GitHub仓库](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge)并采用MIT；四项MUST已有Issue/里程碑，私密漏洞报告及main分支保护已启用。HTTP启动解析与新增路由图片配置修复在隔离发布候选中整合：修复节点四环境CI各525通过，测试契约拆分后的同wheel双安装各526通过，首次失败均保留。候选未替换运行目录：实际部署仍2b479a8，原固定观察及R01/R06/R07/R13未完成状态保持。

先读[AGENTS](../../AGENTS.md)、[统一总览](../../docs/102-user-requirements-and-roadmap.md)、[关键路径](CRITICAL_PATH.md)、[TODO](TODO.md)。同一PRD/矩阵和原checkout继续；主Agent负责集成、GitHub与现场，子Agent仅隔离候选。没有聊天定时任务，不新建。

## 运行版本与发布候选

- 实际部署：`2b479a891833c21c7e03c389f92a4a77ce3ee366` / E143，25模块。原99任务/240 Agent outbox/session、群Kimi/私聊Pi绑定保持；后续Git/公开HEAD不是部署证明。
- 原运行checkout保持`codex/complete-bridge`；`codex/publish-candidate`含HTTP无DNS启动及E144新增路由图片继承修复，未检出覆盖运行字节。候选父图包含原文档HEAD，可在维护窗口快进；不要直接运行GitHub检出的候选顶替现场。
- 新MIT wheel SHA：`ea2d49f4ae33e97d043c9e3c51a211da3a261e233d166a0496ccb44667cc9cfc`。[绑定验证](../../evidence/2026-11-17/combined-candidate-validation.json)区分修复节点云端四环境各525与新测试契约双安装各526。旧E144 pre-MIT wheel不适用于新候选。
- 发布、候选生成工具、原始失败、导出包和最终同步回执均在`local/github-publication-20261117/`；脱敏过程见[E149](../../docs/149-github-public-launch-and-ci.md)。

## 下一项可执行工作

原run `parallel-hardening-24h-20261116`固定北京时间 **2026-11-17 18:29:37.189681** 截止。启动记录`local/parallel-hardening-20261116/observation-launch.json`，采集`local/service-observations/parallel-hardening-24h-20261116/`。到期后审原run，结果写run外；分别核24h完整性、记录错误、固定cut账本覆盖、启动来源和自然refresh。E144前段已有31次history错误/15错误采样并恢复，零记录错误已false，不能用计时结束或后续快照补造通过。

审计后按AGENTS维护流程合入当前候选并部署：先gateway停止、封新调用/排空、停transport/持锁备份，再应用已测代码；transport-only用同一SQLite事务核watermark≥固定cut且无history_window，再次封停审积压，最后恢复原服务。核实际manager归属，不复用历史PID或旧部署脚本。新候选的模块摘要/包/测试必须相符，不套旧E144部署输入。R01不等待其他MUST，但当前非紧急修复不打断原观察。

## 其余验收边界

当前52通过/10阻塞/2部分，R01/R06/R07/R13四项MUST未完整。E146已恢复原CUA并收口私聊原生引用，不重跑旧样本；E134原两条组合完整图文/顺序/身份/AI标识已见，重复旧路径逐图保存仍失败，不重发补截图。WAV/MP4四方向原件下载/播放和MP4视频卡片已验，原生语音条未验；用户尚未明确调整原范围，原判据保持。

Kimi两次订阅403仅限制对应执行器任务；无访问恢复新证据不探测、不重发失败任务或换runtime规避。原R09至少一个执行器已满足，不加四runtime全过门槛。仅AIC及原私聊，不加人/bot/权限、不碰其他群；禁止真实auth/login/doctor、Keychain读锁解锁、复制token、改权限/重启等动作。

## GitHub与收口

仓库已公开MIT，main要求PR与四项Actions检查；禁止直接推main、强推或管理员绕过。GH007邮箱隐私拒绝保留；原本地历史与证据SHA不改，使用`local/github-publication-20261117/history-rewrite_public_history.py`生成仅替换邮箱的等树发布副本。候选生成工具为同目录`create-public-candidate.py`，只用独立临时index，不修改运行文件或实际index；后续候选需保留原分支文档HEAD的祖先关系。网络用精确仓库URL作用域的既有代理，不改全局设置或凭据。

最新工程结果见E149；最新真实部署E143、真实UI E146。测试、公开发布、候选导出不替代现场部署或全部MUST验收；完成后才可签最终交付。每段推进准确更新当前入口/索引、manifest、隐私门与账本，原始身份/聊天/截图/日志/数据库仅留local。
