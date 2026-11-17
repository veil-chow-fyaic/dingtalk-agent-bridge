# DingTalk Agent Bridge

通过官方 DWS CLI，把普通账号的钉钉群聊和私聊接入本地程序。

提供统一 CLI、本机 HTTP API 和持久消息消费者，支持多账号/多会话路由、文件原件、引用、幂等发送与故障恢复。需要自动执行任务时，再接入可选 Agent gateway；通道本身不依赖特定模型、运行器或测试组织。

**当前为开发中的可用工程，尚未完成全部验收。** 基础收发、文件交付和多种执行器已有真实验证；新增路由图片配置、组合图片逐件保存、部分原生媒体类型及长期可靠性仍有待完成项。[查看准确能力](docs/102-user-requirements-and-roadmap.md)及[剩余任务路线图](docs/ROADMAP.md)。

## 可以做什么

| 能力 | 已验证范围与限制 |
|---|---|
| 群聊 / 私聊 | 双向文字、长文、引用；以明确身份和会话 ID 路由，跨组织权限需独立核验 |
| 常用文件 | TXT、CSV、PDF、DOCX、XLSX、ZIP 的代表性原件收发与客户端下载打开 |
| 图片与音视频文件 | PNG/JPEG、WAV/MP4 已有真实样本；MP4 视频卡片播放、WAV 播放器已验；原生语音条及独立 video 协议未完整验证 |
| 单条图文组合 | 文字＋有序图片；双 PNG 已验 API、官方原件和客户端呈现，客户端逐图保存仍未通过；不支持任意多文件合成一个气泡 |
| 程序消费 | HTTP 事件接口、持久游标、附件物化和异常消息隔离；consumer 不自动调用模型或回复 |
| 可选任务执行 | Kimi、Codex、Pi 各有实际工具/会话/交付证据；OpenClaw 适配尚缺真实模型验收，具体范围见[运行器接入表](docs/architecture/agent-integration-map.md) |

DWS 负责认证、通讯、历史、资源和办公能力；bridge 补充路由、持久状态、原件校验和执行控制。PNG/JPEG 原生图片上传使用[窄补充入口](integrations/dws_image_upload/README.md)，复用固定官方实现。单文件上限 20 MiB，原生图片上限 2 MiB。未知投递保留原业务键对账，不自动换键重发。

## 开始使用

需要 Python 3.11+、POSIX 系统，以及你自己的已授权官方 DWS 账号。macOS arm64 已实机验证，其他系统未实机认证。运行包只依赖 Python 标准库；源码构建需要 setuptools。当前适配基线为 DWS v1.0.67。

克隆源码并查看入口：

```bash
git clone https://github.com/veil-chow-fyaic/dingtalk-agent-bridge.git
cd dingtalk-agent-bridge
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/dab --help
```

这几步不会连接钉钉。接下来按[首次使用指南](docs/getting-started.md)填写自己的身份与会话，先启动独立传输，再用 CLI 和 consumer 验证。已有离线交付包可直接[安装已测 wheel](docs/144-offline-release-export.md)，无需重新构建。

默认服务为 `127.0.0.1:18768`，使用本机 Bearer token。所有组件以启动工作目录保存配置和账本；不能复制其他人的 `local/`，也不能把测试会话名称当产品默认值。

## 使用边界

凭据存储故障、受管进程超时或清理失败会持久暂停调用；普通 history API 错误可随正常轮询恢复，两者的处理不同。系统凭据故障的永久根因、自然失效刷新及完整长期可靠性仍未证实。执行器和工具 wrapper 不是 OS 沙箱；启用 gateway 前须明确发送人白名单和执行环境。

当前配置助手 `select` 尚未部署图片 helper 继承修复，新增路由使用图片前须核对 `imageUploadBinary`。模型服务的订阅或访问失败只影响对应执行器，不构成通用 IM 通道的必备依赖。具体操作和限制见[运行手册](docs/15-service-runbook.md)与[安全说明](SECURITY.md)。

## 文档与协作

| 目的 | 入口 |
|---|---|
| 第一次运行 | [上手指南](docs/getting-started.md) · [身份与开通经验](docs/11-onboarding-lessons.md) |
| 集成自己的程序 | [CLI / HTTP / consumer](docs/22-generic-tool-and-consumer.md) · [OpenAPI](api/openapi.json) · [路由模板](config.routes.example.json) |
| 接入执行器 | [运行器支持表](docs/architecture/agent-integration-map.md) · [执行器模板](config.agent.example.json) |
| 运维与排错 | [运行手册](docs/15-service-runbook.md) · [风险与恢复条件](docs/114-dws-risks-and-resolution.md) |
| 参与开发 | [贡献指南](CONTRIBUTING.md) · [变更记录](CHANGELOG.md) · [安全说明](SECURITY.md) |
| 核对范围与证据 | [当前总览](docs/102-user-requirements-and-roadmap.md) · [验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md) · [全部文档](docs/README.md) |

主代码采用 [MIT 许可证](LICENSE)。第三方材料保留各自的许可与[来源声明](THIRD_PARTY_NOTICES.md)。
