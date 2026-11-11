# 原生图片接入 bridge 与真实 Kimi 图片交付

2026-11-11，接续[内联图片缺口](32-native-image-versus-inline.md)。本轮已把本地 PNG 上传与独立 image 消息接入通用 bridge，私聊原件下载打开、真实 Kimi 生成图片交付通过。没有把 API 成功当作 UI 验收；群聊新路径尚未通过。

## 官方与补充边界

| 层 | 发现与实现 |
|---|---|
| 官方发送 | 原版 v1.0.67 的 `chat +messages-send --as user --msg-type image --media-id`，接收明确 profile 与原目标，返回 task ID 后查询发送状态 |
| 官方上传 | `dingtalk-file/upload_media`，参数 `content`（Base64）、`imageType`、`bizType=CHAT_IMAGE`；聊天图片要求 mediaIdV2 |
| CLI 缺口 | 官方在 Markdown 图片内部调用上传，但没有可用的独立 CHAT_IMAGE 上传命令；`chat media upload` 明确下线。市场“文件”“图片”查询未找到该内部服务；直接把 server ID 当 mcpId 的只读发现失败，未猜测其它 ID 或改用审批/表情业务类型 |
| 本地补充 | 固定官方源码加一个 `chat bridge-image-upload` 叶子及一行注册，复用官方 `runImageUpload`、鉴权、profile、MCP transport；隔离构建，不替换原版 DWS。不是官方发布版本 |
| bridge | 路径和原件摘要校验，持久上传/发送状态，旧幂等键兼容，明确使用独立 image；runtime 无关 |
| gateway | 配置了上传入口时，小于等于 2 MiB 的 PNG/JPEG 结果自动以原生图片交付；其它文件仍按原文件通道交付。runtime 的 `text/files` 契约不变 |

源码依据：[官方聊天上传实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/chat_image_upload.go)、[官方通用上传原语](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/image_upload.go)、[已下线媒体入口](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/chat_media_upload.go)、[独立图片发送](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/chat/unified_send.go)。构建方法与许可证边界见[补充入口说明](../integrations/dws_image_upload/README.md)。

## 状态与恢复

新 `image` 请求先保留原 payload 指纹，再在 SQLite 同一事务中记录 `deliveries.uploading` 与 `image_uploads.uploading`。上传成功保存 mediaId，提交发送 reservation，随后才调用原版 DWS 发独立 image；正常经 `submitted` 到 `confirmed`。

上传失败或超时标 `upload_unknown`，且消息发送没有被调用；重启或重复同 key 都不重传、不发消息。上传成功后的发送中断保持 `outcome_unknown` 并保留 mediaId；有 task ID 则只查询状态，无 task ID 保留未知待对账。没有静默重试、Markdown 降级、换 key 或 UI 代发。上传本身官方没有独立结果查询接口，因此这里保守停留，不宣称能自动恢复所有上传失败。

旧内联图记录的 payload/fingerprint 不改变，升级后同 key 返回旧回执。不会把历史 confirmed 图自动转换或补发。两路升级前 51 条投递记录逐字段保持；私聊 gateway 原 14 个任务（含一个历史 blocked）和 34 条投递未改写。源码不删除历史失败。

图片保持原始字节，服务限制 2 MiB，不进行有损压缩。桥接入口检查 PNG/JPEG 文件头、扩展名和 staging SHA；完整解码/其它尺寸和格式场景仍需另验，不能将本次 PNG 外推成所有 JPEG/动画/超大图通过。

## 用户侧现场

| 案例 | 实际动作及结果 |
|---|---|
| bridge 原件私聊 | 新实验 `DAB-BRIDGE-NATIVE-PNG-20261111-direct-001`，HTTP image 请求→补充上传→原版 DWS 独立 image；veil 客户端左侧 liev 图片和“通过AI发送”，查看器、下载、Finder Quick Look 均通过 |
| 实际任务 | veil 在钉钉私聊发送 `DAB-NATIVE-RESULT-20261111-DM`，要求 Kimi 用 Python 标准库生成 96×64、RGB(0,100,200) 的 PNG；Kimi 实际执行，收到确认、结果文字、独立图片共 3 条确认投递 |
| 结果获取 | 用户侧双击蓝色图片打开查看器，点击下载，Finder Quick Look 显示蓝色矩形。246 B 原件与 runtime 产物字节一致；独立解析 PNG 尺寸与全部像素通过，不以模型自报正确为证据 |
| 群聊新路径 | 发前 DWS 查到原群成员已从 2 变成 3。按本轮原两账号范围，尚未发送本轮群图，已询问是否继续在原 3 人群实测；不新增群/成员、不修改权限，私聊独立继续。旧群矩阵证据保留，但不冒充新原生图片路径通过 |

1853 B fixture 的 SHA-256：`14bc34d2e2aed2a70b0371def3f39f8c8dc344c3bf998229c7cb83893781c582`。
246 B 生成结果的 SHA-256：`ecdd707aeed67d0cb0fd571fb8a4657e192e97f0ecb42f7be706c4ab8057e0fb`。

UI 曾先捕获 Finder 选中文件，未算打开通过；后用 Quick Look 真正显示原件。生成图查看器初帧标题尚未稳定，下载完成后显示“liev分享的图片 246字节”，以稳定状态与历史发送身份核验。原始截图、AX、意图、profile、回执、资源和客户端文件只保存在 `local/native-image-bridge-20261111/`。

## 验证与限制

- Python 全套 84 项通过，新增上传超时、上传/发送间崩溃、重启不重传、旧 Markdown key、损坏 staging、无效/V1/压缩上传回执和 gateway 图片选择场景。
- 补充 Go 叶子的 6 个用例（成功、dry-run、伪图片、超限、业务失败、只有 V1）及上游 schema 完整性检查通过。CLI dry-run 不上传、不发消息，运行时 compact schema 可查到此补充叶子。
- [只读验收脚本](../scripts/accept_native_image_bridge.py)核对上传表、确认投递、观察到的资源、两份客户端下载原件、真实任务、像素和旧账本；[脱敏账本](../evidence/2026-11-11/native-image-bridge-ledger.json)、[UI 观察](../evidence/2026-11-11/native-image-bridge-ui.json)。已有写入实验不重放。
- 20:54 因部署本功能重启了传输，随后重启私聊 gateway；24h 原观察器没有重置。采样正常不能证明部署期间零中断，更不能称同一版本连续运行 24h。保留此维护窗口，最终按时间和版本分段分析。

下一步：在范围确认后补原群原生图片 UI；无需等待此项即可继续私聊音视频、引用与多附件、运行交付和办公能力。当前仍不是完整交付，心跳保持。
