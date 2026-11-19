# DingTalk Agent Bridge

[![CI](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/actions/workflows/ci.yml)

让本地程序和 Agent 通过普通钉钉账号，在已有群聊和私聊中收发文字与文件。

项目优先使用官方 DWS CLI，提供独立的命令行工具、本机 HTTP API 和持久消息消费者。需要让 Agent 执行任务时，可以接入 OpenClaw 原生通道或可选 gateway。基础 IM 不依赖特定模型、Agent runtime 或测试组织。

**核心 IM 和 OpenClaw 双路文件任务已有真实收发与客户端下载验证，项目仍在持续开发。** 原生语音条出站、部分媒体和真实会话生命周期尚未完成全部验收。具体范围见[能力总览](docs/102-user-requirements-and-roadmap.md)。

[开始使用](docs/getting-started.md) · [接入 OpenClaw](integrations/openclaw-channel/README.md) · [接口参考](docs/22-generic-tool-and-consumer.md) · [文档导航](docs/README.md) · [已有组织工作区试点](docs/resident-openclaw-pilot.md)

## 能做什么

| 使用场景 | 当前能力与范围 |
|---|---|
| 群聊和私聊收发 | 双向文字、长文与引用；按明确账号和会话 ID 路由 |
| 获取和回传文件 | TXT、CSV、PDF、DOCX、XLSX、ZIP 等代表性原件已验证收发、下载和打开；单个输出文件上限 20 MiB |
| 发送图片与图文 | PNG/JPEG 原生图片，每张不超过 2 MiB；群、私聊的文字加双 PNG 及逐图保存已实测 |
| 音视频文件 | WAV/MP4 双向原件、下载与播放已验，包括钉钉 MP4 视频卡片；不外推全部编码或长音视频 |
| 收取原生语音 | 群聊和私聊录音可取得原件、解析并交给 consumer；主动发音频可用 WAV 附件，聊天语音条出站尚未实现 |
| 接入自己的程序 | CLI 与 HTTP 读写消息；consumer 保存游标、整理消息与附件，不自动调用模型或回复 |
| 交给 Agent 处理 | 可选执行器读取附件、执行工具、把结果回传原会话；多文件可以关联同一任务，任意多文件单气泡尚未实现 |

DWS 负责身份、通讯、历史和资源；bridge 补充路由、白名单、持久状态、幂等发送、原件校验和恢复。原生图片发送还需配置[图片上传补充工具](integrations/dws_image_upload/README.md)，它复用固定官方实现。跨组织、多人及更多格式的范围以[验收矩阵](plans/completion/ACCEPTANCE_MATRIX.md)为准。

## 开始使用

准备 Python 3.11+、POSIX 系统和你自己已授权的官方 DWS 账号。当前 DWS 适配基线为 **v1.0.67**，二进制不随 Python 包分发。已有满足权限要求的组织和会话即可使用，无需为了 bridge 新建组织或 bot。

真实钉钉业务已在 macOS arm64 验证。CI 在 Ubuntu 24.04、macOS 15 的 Python 3.11/3.14 上运行离线检查；这不代表其他系统的真实 DWS 业务已获认证。Python 运行包只用标准库，源码构建需要 setuptools 77.0.3+。

```bash
git clone https://github.com/veil-chow-fyaic/dingtalk-agent-bridge.git
cd dingtalk-agent-bridge
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/dab --help
```

以上步骤只安装并显示帮助，不调用 DWS；构建时可能下载 setuptools。需要离线安装时，使用[已测 wheel 的导出与安装流程](docs/144-offline-release-export.md)。

接下来按[首次使用指南](docs/getting-started.md)填写自己的 profile、会话 ID 和路由。先用 `dab-bridge` 启动独立传输，再用 `dab` 收发、`dab-consume` 持续消费。`dab-agent` 是可选任务执行入口，`dab-service` 管理后台服务，`dab-doctor` 提供本地诊断。

服务与配套 CLI/consumer 默认使用 `127.0.0.1:18768` 和本机 Bearer token。在同一工作目录运行各组件，让它们使用同一份配置和账本。身份、聊天、下载、令牌等私有状态保存在自己的 `local/` 中，不复制其他人的工作目录。

## 收发示例

完成配置、启动传输后，在同一工作目录执行。`ACCOUNT`、`CONVERSATION`、`BUSINESS-KEY` 均为占位符，须换成已核实的路由和本次发送意图的唯一键；`send` 会真实发送。

```text
.venv/bin/dab --account-id ACCOUNT --conversation-id CONVERSATION events --after 0 --limit 100
.venv/bin/dab --account-id ACCOUNT --conversation-id CONVERSATION send --key BUSINESS-KEY --text "报告已准备好"
.venv/bin/dab --account-id ACCOUNT --conversation-id CONVERSATION status --key BUSINESS-KEY
```

全局路由参数写在子命令前。投递结果未知时只按**原 key**查询和对账，不换 key 重发；CLI 退出成功或 HTTP 202 不代表消息已确认，`confirmed` 也不代表对方已读。文件、图片、引用和持续消费用法见[接口参考](docs/22-generic-tool-and-consumer.md)与 [OpenAPI](api/openapi.json)。

## 可选：接入已有 Agent

已有 OpenClaw 的用户可以把钉钉群聊和私聊绑到自己的组织 Agent。Agent 共用其工作区和工具，每条会话保留独立的上下文和回复目的地。每条钉钉路由由一个执行器接单，发送人白名单决定谁能使用该工作区。 [插件配置](integrations/openclaw-channel/README.md)

普通群消息只接收，`/agent` 才交办任务；私聊按白名单接收。群附件可按[插件说明](integrations/openclaw-channel/README.md#use-the-channel)用精确文件名关联。更多运行器的实现与实测范围见[接入表](docs/architecture/agent-integration-map.md)。

常驻宿主已实测群聊、私聊文件交办及独立追问。完整切回原执行器后，再次接入同一组织 Agent，两路都保留原会话。用户发 `/stop` 能中止正在执行的任务；现场一笔已中止的输入缺少取消关联，仍会阻止严格回切。后续独立查询正常。 [常驻验收与当前限制](docs/resident-openclaw-pilot.md#再次接管与运行中取消)

## 运行与排错

凭据存储故障、受管进程超时或清理失败会持久暂停调用；普通 history API 错误可以随正常轮询恢复。未知投递不会因此自动重发。先按[运行手册](docs/15-service-runbook.md)和[故障分类](docs/114-dws-risks-and-resolution.md)处理，保留账本和原键。

正常凭据续期已有实测，失效 refresh 凭据恢复仍有未验证范围；持续运行观察保留了真实错误与恢复记录，不作零故障承诺。启用任务执行前应明确白名单和执行环境，gateway 与工具 wrapper 不提供 OS 沙箱。详见[安全说明](SECURITY.md)、[媒体操作与限制](docs/151-native-voice-and-image-saving.md)以及[部署和故障证据导航](docs/README.md#验收与历史证据)。

[贡献指南](CONTRIBUTING.md) · [变更记录](CHANGELOG.md) · [后续路线](docs/ROADMAP.md) · [全部文档](docs/README.md)

主代码采用 [MIT 许可证](LICENSE)。第三方材料保留各自的许可与[来源声明](THIRD_PARTY_NOTICES.md)。
