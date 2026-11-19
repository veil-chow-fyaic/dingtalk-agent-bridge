# DingTalk Agent Bridge

[![CI](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions/workflows/ci.yml)

通过官方 DWS CLI，把普通账号的钉钉群聊和私聊接入本地程序。

提供统一 CLI、本机 HTTP API 和持久消息消费者，支持多账号/多会话路由、文件原件、引用、幂等发送与故障恢复。需要自动执行任务时，再接入可选 Agent gateway；通道本身不依赖特定模型、运行器或测试组织。

**可用于普通账号的群聊和私聊。** 已验证文字、文件、引用、接收原生语音、组合图片逐张保存，以及由真实工具处理后回传文件。普通账号通过 bridge 发音频时可用 WAV 附件；原生语音条出站尚未实现。[能力与范围](docs/102-user-requirements-and-roadmap.md) · [交付路线图](docs/ROADMAP.md)

核心运输已登记检查点仍为E150 / `0e151fb`；E154记录过临时canary接管及旧gateway退让，当前归属与后续部署须另按实际收据核对。 双路文件验收已满足，可进入[PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9)的合并检查；是否已合并以实际GitHub回执为准。部署收据尚待单独取得，不由本次验收推定正式部署。

14 项 MUST 已通过 13 项，R06 媒体验收为部分通过。[原判据与四方向矩阵](plans/completion/ACCEPTANCE_MATRIX.md)

OpenClaw原生通道的群聊和私聊真实文件验收已通过。新群商品筛色任务独立于E154旧未知出库单。[安装](integrations/openclaw-channel/README.md) · [E155结果](docs/155-openclaw-two-route-file-acceptance.md) · [PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9)（合并与部署收据）

## 可以做什么

| 能力 | 已验证范围与限制 |
|---|---|
| 群聊 / 私聊 | 双向文字、长文、引用；以明确身份和会话 ID 路由，跨组织权限需独立核验 |
| 常用文件 | TXT、CSV、PDF、DOCX、XLSX、ZIP 的代表性原件收发与客户端下载打开 |
| 图片与音视频文件 | PNG/JPEG、WAV/MP4 群/私聊双向已有真实样本；MP4 视频卡片播放、WAV 原件下载和播放器已验，不外推全部编码、长音视频 |
| 原生语音条 | 群聊、私聊真实录音均已取得可解码原件、进入独立 consumer，并在客户端播放。固定 DWS 普通账号转发仅产生文字；主动发送可用 WAV 附件 |
| 多文件任务 | 多条附件关联同一任务、实际工具处理、文件回原会话及客户端下载打开已有真实验证；不等于任意多文件合成一个消息气泡 |
| 单条图文组合 | 群聊、私聊各验一条双 PNG 消息。可从会话「文件」进入「图片及视频」，选中缩略图，在查看器中下载并保存，四张原件均已打开并核对 SHA-256。任意多文件同一气泡仍未实现 |
| 程序消费 | HTTP 事件接口、持久游标、附件物化和异常消息隔离；consumer 不自动调用模型或回复 |
| 可选任务执行 | Kimi、Codex、Pi 各有实际工具/会话/交付证据；OpenClaw原生通道E155双路文件已实测，E154旧未知单独保留；内置CLI适配另计，具体范围见[运行器接入表](docs/architecture/agent-integration-map.md) |

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

凭据存储故障、受管进程超时或清理失败会持久暂停调用；普通 history API 错误可随正常轮询恢复，两者的处理不同。[正常自动续期](docs/47-natural-auth-rollover.md)已有真实证据；过期或撤销 refresh 凭据后的恢复、系统凭据故障的永久根因仍未证实。执行器和工具 wrapper 不是 OS 沙箱；启用 gateway 前须明确发送人白名单和执行环境。

原 `parallel-hardening-24h-20261116` 于北京时间2026-11-17 18:29:37固定截止自然封存：2877采样、0不可达、18错误采样/29路由错误记录、1新事件、0重复、0维护；13完整性与29项截止/来源检查全部通过。29个已观测路由错误均有后续同路新完整同步/清错，保守观测上界30.187秒，无未恢复/未知采样。完整24h、双路同事务水位覆盖及启动来源通过；zero_recorded_errors/stability_pass仍false，不承诺零故障、上游无丢失或本run自然refresh。

源码中的配置助手 `select` 已修复同账号新增路由的 `imageUploadBinary` 继承；生成配置后仍须核对自己的身份、目标及 helper 路径。模型服务的订阅或访问失败只影响对应执行器，不构成通用 IM 通道的必备依赖。具体操作和限制见[运行手册](docs/15-service-runbook.md)、[语音实测与逐图保存方法](docs/151-native-voice-and-image-saving.md)及[安全说明](SECURITY.md)。

## 文档与协作

| 目的 | 入口 |
|---|---|
| 第一次运行 | [上手指南](docs/getting-started.md) · [身份与开通经验](docs/11-onboarding-lessons.md) |
| 集成自己的程序 | [CLI / HTTP / consumer](docs/22-generic-tool-and-consumer.md) · [OpenAPI](api/openapi.json) · [路由模板](config.routes.example.json) |
| 接入执行器 | [运行器支持表](docs/architecture/agent-integration-map.md) · [OpenClaw、Hermes 与 DeepSeek Harness 接入调研](docs/152-community-agent-adapters.md) · [执行器模板](config.agent.example.json) |
| 运维与排错 | [运行手册](docs/15-service-runbook.md) · [风险与恢复条件](docs/114-dws-risks-and-resolution.md) |
| 参与开发 | [贡献指南](CONTRIBUTING.md) · [变更记录](CHANGELOG.md) · [安全说明](SECURITY.md) |
| 核对范围与证据 | [当前总览](docs/102-user-requirements-and-roadmap.md) · [验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md) · [全部文档](docs/README.md) |

主代码采用 [MIT 许可证](LICENSE)。第三方材料保留各自的许可与[来源声明](THIRD_PARTY_NOTICES.md)。
