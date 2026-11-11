# 当前运行说明与工具契约核对

2026-11-12，E050。本段解决交接文档中已过时的身份、进程管理和接口说明；没有修改产品代码、现网配置或重新发送已完成实验。

## 发现与修正

[运行手册](15-service-runbook.md)前半段已写统一管理器，后半段却仍说旧ctl管理当前检出、统一管理未完成，并列历史95项及已处置的unknown计数。[通用工具说明](22-generic-tool-and-consumer.md)仍写只测单人群、私聊跳过和51项测试，容易让接入者沿用错误前提。

已将这两份旧全文从`aaa5cf2`按字节存入[历史目录](history/through-E049/README.md)，当前页改为安装/工作目录、明确身份、manager启动、路由、CLI、consumer及恢复的现行说明。历史实验和错误不删除；[原安装检查点](35-install-and-doctor.md)开头明确它是E015五入口历史，当前六入口以运行手册为准。

逐项对照源码和已安装命令帮助，补清以下边界：

- 随包CLI、gateway、consumer及manager使用127.0.0.1:18768；只有前台传输支持单独改端口，不能把它理解成整套组件都可配置。
- 公共路由模板没有receiveMode时默认history；stream_hint及imageUploadBinary需显式配置。configure select生成候选配置，不继承这两个可选字段、不自动激活会话，输出必须不存在。
- `send` HTTP 202及CLI退出0仍需看state，包含重读旧rejected的情形；status/reconcile不重新发送。纯文本引用使用reply_to，文件/图片只传允许的服务工作目录路径。
- [OpenAPI](../api/openapi.json)补原已实现的rejection_evidence参数、POST 1MiB/413及内部错误500。拒绝日志核对原key、目标、执行窗口、长度和持久payload摘要；不是任意聊天附件自证，也不能把无task ID的未知自动改成成功。
- 通用consumer仅持久消费/物化媒体；实际模型调度在独立gateway或调用方。官方授权、真实普通账号、原生媒体、原件和UI证据仍分别表述。

## 验证与证据

公共报告：[handoff-contract-validation.json](../evidence/2026-11-12/handoff-contract-validation.json)。13项核验、12项现场记录保持检查通过。

在E048已安装Python3.11.15 wheel、空工作目录中，清除继承PYTHONPATH，确认import来自site-packages；六入口、九个dab子命令和configure三个帮助入口，共18次均退出0，关键文档参数存在，没有初始化工作目录。两个公共配置模板仅离线解析结构及默认600秒；占位符不等于可运行账号配置。

同一已安装wheel在不含源码包或账号数据的隔离测试目录运行既有四组测试：HTTP/Stream 3、拒绝对账8、迁移/发现/延迟消费9、路由/consumer 13，共33项通过。HTTP组实际启动本机合成子进程服务验证鉴权、选择、事件唤醒、引用及停止；不是实机DWS/UI测试。OpenAPI核验为JSON语法与已实现字段/状态码的人工对照，没有声称完整第三方规范验证。

19个产品模块与E048摘要相同，两份历史存档与Git原文件逐字节相同。三受管进程归属保持，未构建或重载；两路jobs/outbox/meta/deliveries/events/runtimeFiles共12项保持，未新增消息或UI通过。私有帮助输出、测试日志、运行快照与只读验证脚本在`local/handoff-contract-20261112/`。

最终快照DM61任务/151outbox/160传输/222事件，群3/7/12/76。原观察器1358样本、11.319小时、6不可达，原3个poll_error及维护保留，尚未满24h；最早11月12日19:36:08终检。本段不改任何MUST/SHOULD判据，整体交付仍未完成。
