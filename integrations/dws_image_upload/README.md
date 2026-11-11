# DWS 聊天图片上传入口补充

这是本项目的本地补充命令，**不是官方发布的 DWS 命令**。固定上游 v1.0.67，commit `63a7c4906c7dee10750011ea309b9eb78abb7eb0`。原版二进制继续负责历史、订阅、资源下载和消息发送；补充二进制只用于上传图片。

官方已有 `CHAT_IMAGE` 上传实现和 `--msg-type image --media-id` 发送；但 v1.0.67 未暴露独立的聊天图片上传叶子，`chat media upload` 已下线。`mcp published tools dingtalk-file` 也不能把内部 server ID 当市场 mcpId 使用。本补充仅增加 `chat bridge-image-upload --file` 声明及一行注册，调用官方 `runImageUpload`，不读取、复制或实现 token、OAuth、MCP HTTP 协议。详见[现场边界与验收](../../docs/33-native-image-bridge.md)。

默认保留原件：不自动压缩，最大 2 MiB。bridge 接受 PNG/JPEG；更大图片可明确选择普通文件发送。上传仅返回 mediaIdV2，不向聊天发消息，不收藏表情，不修改审批。认证仍使用明确传入的 DWS profile。

在项目目录中，安装官方 Go 1.26.7 或兼容工具链后：

```bash
git clone --depth 1 --branch v1.0.67 https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli.git local/dws-image-source
python3 integrations/dws_image_upload/build.py --source local/dws-image-source --go /absolute/path/to/go --output local/bin/dws-image-upload-v1.0.67/dws-image-upload
```

构建会验证固定 commit、拒绝覆盖非预期已跟踪源码修改，复制本目录的叶子和测试，只在这份专用源码工作副本添加注册；先运行 6 个上传用例和上游命令/schema 完整性检查，再构建。构建回执包含源 commit、补充文件摘要、Go 版本及二进制摘要。依赖与上游许可证保留在上游工作副本；上游采用 [Apache-2.0](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/LICENSE)。没有分发或修改系统安装的 DWS。

只在需要启用图片的现有路由中增加：

```json
{"imageUploadBinary":"local/bin/dws-image-upload-v1.0.67/dws-image-upload"}
```

`binary` 仍指向原版 DWS。配置后按运维手册重启传输和对应 gateway。先只读核验原投递账本，再用新的明确实验验收；禁止重发旧 key。未配置补充入口时，新的 `image` 请求明确失败，不会暗中改发 Markdown。旧 key 仍返回原回执。

将来官方发布等价独立上传命令，应替换这个薄入口并重新验证原件和身份，不必更改 runtime 协议。
