# 通用工具边界与运行器接入

已有 OpenClaw 可以让授权钉钉会话使用同一组织 Agent。E159 的常驻宿主实测覆盖双路文件、独立两轮和钉钉通道恢复。 [插件配置](../integrations/openclaw-channel/README.md) · [现场验收](resident-openclaw-pilot.md#现场验收)

E132（2026-11-16）整理。产品是通用IM中间件，任何Agent/程序可使用CLI/HTTP/持久consumer；用户无需先选某个runtime才能开发或使用通道。E133新增、E134部署CLI/HTTP的composition，接收字面文字和逐张绑定SHA的有序图片；不改gateway的现有逐件交付，见[接口说明](22-generic-tool-and-consumer.md)。组织/profile、精确会话及运行器都是配置，不能将测试群写入产品逻辑。

## 当前接入层次

| 层次 | 责任 | 使用入口 |
|---|---|---|
| 传输 | 显式账号/会话路由，history与持久水位，消息/原件，发送账本与原key对账 | [CLI/HTTP手册](22-generic-tool-and-consumer.md) · [OpenAPI](../api/openapi.json) |
| 通用consumer | 事件/游标同事务落盘，物化有序parts/quote/附件，self过滤，异常隔离 | [持久消费说明](22-generic-tool-and-consumer.md) |
| 可选gateway | 白名单/群命令触发、任务和原生session、取消/new、结果校验与outbox | [运行手册](15-service-runbook.md) |
| 原生 OpenClaw 通道 | 已有宿主接管指定的钉钉路由，按原账号回传正文及本地结果文件 | [常驻试点与回切](15-service-runbook.md#已有-openclaw-的常驻钉钉试点) |
| runtime adapter | 本地工具、原生终态/session/中断，按实际能力交付 | [四类运行器状态](architecture/agent-integration-map.md) |

原 R09 至少一个本地执行器已满足。内置 OpenClaw CLI 薄适配走本项目 gateway，其模型契约有合成验证。原生 OpenClaw 通道由宿主驱动，实测范围见 E155、E159。Kimi 已记录的 403 仅限对应模型任务。 [执行器边界](architecture/agent-integration-map.md) · [能力总览](102-user-requirements-and-roadmap.md)

## 消费和身份边界

Hub按账号/会话分路，名称只展示；profile留内部配置。同一consumer名字绑定一路，flock防同名并发。事件与游标先持久化，再下载/规范化；normalized不代表模型已经执行，ready()是筛选接口，不是acked状态。

本人和未知sender不生成普通可触发消息；allowSelfCommands只覆盖已核身份的显式命令，不关闭通用self过滤。quote保留原目标/原文/已暴露身份字段，未知ID保持未知；显示名不能授权。平台资源未物化不能假称模型已读，引用附件不重复放入顶层。

更换runtime必须原生new归档、零未决、显式binding迁移；不只改JSON或清空session。一个消息只由一个任务宿主执行，OpenClaw通道插件和本项目gateway不能同时消费同一路任务。

## 参考和历史

早期WeCom工具只作需求/交互参照，未承诺兼容其WebSocket线协议，也不采用另一项目的Bot-only限制。当前官方/GitHub优先，CEO任务/交付/runtime契约和Qwen通道事务取舍见[参考采用账](references/adoption-plan.md)，不唤醒或修改其他本地项目。

初期18条self消费、51项回归及两轮Kimi任务属于2026-11-11历史，见[初期接入报告](24-local-agent-product-and-acceptance.md)和Git原页；不作为当前总量或Codex仍不可用的依据。
