# 独立IM图文组合候选与Kimi单次复查

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-16，E133。用户明确纠正主线：项目是通用钉钉IM通道，Kimi服务拒绝不能阻塞所有后续工作。本轮实现独立CLI/HTTP组合发送候选，未部署、未发送真实钉钉组合消息，最近真实UI仍E131，部署仍e7d82cc/E123。51通过/11阻塞/2部分及7 MUST保持。

## 已完成的产品变更

`POST /v1/send`新增与text/file/image互斥的composition；`dab send --composition-json`读取同一对象。输入为字面文字与1–9个有序PNG/JPEG条目，每项path和预期sha256必填、每张≤2MiB。文字转义，生成正文含暂存路径按5120 UTF-16单元封顶；不接受远程图片、用户Markdown或普通文件数组。

先验证全部原件，再原子发布内容寻址暂存，保存正文、顺序、名称及摘要组成的指纹；一个业务键只创建一次投递。复用固定官方v1.0.67的`+messages-send --markdown`进行内部上传和一条图文消息发送。未知结果、进程中断和重启均不自动再次上传/发送；有task_id继续原task对账。同key源文件删改仍可返回原回执，改正文、顺序或摘要则拒绝。

这是显式图文入口，不会改变既有独立原生image、单file或gateway逐件交付行为；不要求Kimi、Pi、Codex、OpenClaw等runtime。API与用户说明见[通用接口](22-generic-tool-and-consumer.md)。

## 官方依据与验收边界

本轮读取已冻结v1.0.67源码：`chat_markdown_images.go`、`chat_markdown_image_upload.go`和`unified_send.go`。固定入口已有最多9本地图引用、内容去重上传及一次个人Markdown消息；无需重新运行E056的旧dry-run或重写上传协议。bridge限制≤2MiB，以避开官方大图压缩路径；只能保证本地交给DWS的字节，不能据此断言服务端/客户端保留原件。

E056的计划证据、E011内联图原件获取失败均保留。该候选尚未真实验证群/私聊图文呈现、逐原件获取与SHA，不提升R07；普通多文件单消息、原生语音和独立video仍无本轮新入口。本轮首次原生DingTalk UI读取返回`failedToCreateImageDestination`，未获得新界面；没有重复旧菜单、绕工具限制、改权限或重启系统。

## Kimi：按用户新授权的一次最小请求

现有CLI帮助未暴露只读额度命令，provider子命令只有配置管理。随后用原Kimi CLI默认模型配置、独立临时工作目录、显式空skills目录做一次“仅回复OK，不调用工具”的非交互请求；没有指定旧session或重发E131。该请求沿当前进程环境执行，没有重载gateway的私有runtime.environment，不能代替受管群任务的恢复验收。

约1.7秒退出1，仅system.version事件；stderr仍为`provider.auth_error: 403`及订阅无法访问Kimi Code的提示，无周限额、重置时间、工具或完成事件。自有CLI进程组清理完成；助手未执行登录/doctor、直接读取或复制凭据、认证修复，也没有钉钉消息或gateway任务；请求使用CLI既有正常凭据机制。用户提出周限额是可能解释，现有返回不足以确认。无新授权/恢复证据不循环探测。

## 验证和下一步

新增14个核心方法及1个实际回环HTTP/CLI方法，覆盖有序原件、单次发送、直接会话目标、摘要拒绝、9图/重复引用、路径/大小/扩展名及文件头边界、字面文字、指纹冲突、并发同key、崩溃恢复、未知/拒绝与原task对账。HTTP链路使用合成DWS可执行文件并实际读取暂存字节，不调用账号或模型；源码首轮15方法通过。

最终冻结源码Python3.14.6、同一wheel安装Python3.14.6和3.11.15各448方法通过（每套含新增15方法）；23产品模块/许可字节一致，180份tests/scripts/fixtures/api文件按本轮范围冻结，不能与旧轮次不同口径的素材数直接相加。最终文档另做本轮索引/历史正文/链接核对，不能把冻结测试时的文档快照当成最终交接。冻结版本、同wheel双Python、模块/许可/素材及入口检查结果记录在[脱敏证据](../evidence/2026-11-16/outbound-composition-validation.json)。这是新核心/API变更的兼容性回归，不重做旧真实宿主、UI或观察实验；六CLI只比对定义，本轮仅执行有新参数的dab send --help。

下一步在原生UI可读后，按部署前固定cut/积压/原key核对规则评估候选部署，用新样本完成独立IM单消息及逐原件验收；不以Kimi恢复作为这一通道验收的前提。绑定Kimi的群模型处理/交付仍单独等待服务访问恢复。普通多文件、私聊入站引用、原生voice/video、R13自然续期/长期/截止、最终当前版交接各自按原标准保持未完成。

原始帮助、CLI输出、测试日志/冻结源码及本地工作记录仅在local/next-channel-20261116；无账号ID、原聊天、token、数据库或截图进入Git。
