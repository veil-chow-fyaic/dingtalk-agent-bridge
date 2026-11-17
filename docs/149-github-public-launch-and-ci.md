# 公开仓库上线、启动修复与托管验证

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->

2026-11-17，E149。项目已公开并采用MIT，工程检查和分支保护已落地；原产品验收仍有四项MUST未完成。当前真实部署为`2b479a8`，本轮修复作为独立发布候选保留，未覆盖正在观察的运行目录。

## 仓库与发布范围

[公开仓库](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge)默认分支main，保留原第三方许可及NOTICE；[四任务里程碑](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/milestone/1)、Issue/PR模板、贡献/安全说明和依赖更新已配齐。[私密漏洞报告](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/security/advisories/new)已启用。main要求PR、四项真实Actions检查、解决评审讨论；管理员同样受约束，禁止强推和删除，当前单维护者不要求额外审批人数。

GH007邮箱隐私拒绝按E148保留；只在隔离发布历史中替换邮箱，不关闭隐私保护、不替换原本地历史。发布候选`366212deda4656deb509a8c2ae6c7dad1a807e6a`与原候选`22fea9955dba5eddac78cd4c1632e3849e33e952`等树，tree为`913555a38af80175c60fd0c88b3757d13c93002f`。原历史SHA按[映射](../evidence/2026-11-17/github-history-map-6706175.json)及后续阶段记录追溯；这些源码标识都不是现场部署SHA。

## 实际启动问题与修复

首轮[44036471963](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions/runs/44036471963)中，Ubuntu双Python各519通过，macOS双Python各11失败。[首次失败](../evidence/2026-11-17/github-ci-initial-failure.json)保持原样。第二轮[44038398119](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions/runs/44038398119)保留原8秒断言并捕获4秒栈：两个macOS子进程存活且token已创建，均阻塞在`socket.getfqdn → HTTPServer.server_bind`，服务尚未开始处理请求。

新`LoopbackHTTPServer`只接受字面`127.0.0.1`，复用原`TCPServer.server_bind`设置和实际端口，省去无用的反向主机名解析；没有全局修改DNS。原产品运行新增回归会失败，修复后禁用主机名解析仍可启动、认证、发送原件、重放并正常关闭。为什么托管系统的解析会阻塞未查明；这是已证的启动依赖修复，不是Keychain或其他DWS故障的根治结论。

E144同账号新增路由的`imageUploadBinary`继承修复一并整合，跨账号不借用helper，未改变现有固定DWS。两项只改既有产品模块，仍为25模块。

## 验证层次与失败保留

[修复run 44041215622](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions/runs/44041215622)四环境全部成功；[精确job/范围](../evidence/2026-11-17/github-ci-fix-validation.json)逐项记录。

| 实际环境 | 源码方法 | 独立构建wheel的元数据/模块/许可核对 |
|---|---:|---|
| Ubuntu24.04 / Python3.11 | 525通过 | 通过 |
| Ubuntu24.04 / Python3.14 | 525通过 | 通过 |
| macOS15 / Python3.11 | 525通过 | 通过 |
| macOS15 / Python3.14 | 525通过 | 通过 |

另构建MIT wheel `ea2d49f4ae33e97d043c9e3c51a211da3a261e233d166a0496ccb44667cc9cfc`。初次独立安装的3.11全525通过，3.14有一项`called`就绪标记缺失，[首轮记录](../evidence/2026-11-17/combined-candidate-installed-initial.json)仍为失败。带证据诊断又复现一次，后续细阶段样本通过；原缺标记的系统细因未确定，不能用一次通过追补失败。

[测试契约修正](../evidence/2026-11-17/office-timeout-contract-validation.json)将真实CLI的2秒deadline/持久暂停/禁止重试，与已准备好后代的超时清理分开。仅后者的合成构造器先等待真实`called`与`child.ready`，准备阶段最多10秒且失败会真实清理；之后原`run_dws`仍使用原时钟和2秒期限。缺清理、自动重试负例均被拒绝；慢准备和永不准备分别按预期通过/失败，无活子进程遗留。产品wheel字节未改。

新契约增加1方法，同wheel在Python3.14.6与3.11.15安装后各526项完整通过，运行后再次核25模块/许可/元数据且测试目录没有产品源码。[绑定验证](../evidence/2026-11-17/combined-candidate-validation.json)明确区分云端旧契约525与安装新契约526，不写成526×3。最终提交的后续托管状态以[实际Actions](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions)为准；CI不是实际钉钉账号或模型测试。

## 部署与剩余验收

公开发布与现场部署分离：候选ref`codex/publish-candidate`包含产品修复及本轮资料，主运行目录维持`codex/complete-bridge`的原25模块。原固定run `parallel-hardening-24h-20261116`于北京时间2026-11-17 18:29:37截止；先审原run，再按受管停止/排空/备份、transport-only固定cut与同事务水位、再次停传输审积压的顺序合入部署。新MIT候选不复用旧E144 pre-MIT wheel作为新包。

当前52通过、10阻塞、2部分，R01/R06/R07/R13仍未完整。MP4视频卡片/播放与WAV文件播放器已有真实证据；原生语音条、组合逐图保存、Kimi对应任务与自然refresh保留各自边界。未降低原标准，未执行真实auth/Keychain或服务维护，没有新建聊天调度，也未发布稳定版完成声明。
