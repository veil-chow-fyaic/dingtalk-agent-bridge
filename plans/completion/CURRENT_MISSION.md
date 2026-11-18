# 当前任务

E153 工作分支为 `codex/native-agent-channel`，起点是已核对的公开主分支 `e4b650f`。产品消息默认由宿主决定，原生 OpenClaw 通道与内置 gateway 分路独占。[E153 实现与验收](../../docs/153-channel-presentation-and-openclaw.md)

当前主线是让已有 Agent 宿主复用普通账号群聊和私聊的双向文字、文件与会话能力。E152 已完成原始需求和社区项目核对，首选交付 OpenClaw 原生通道，再用 ACP 对接 Hermes 和 DeepSeek Harness。[E152 适配器调查](../../docs/152-community-agent-adapters.md)

用户已授权实现、现场测试、文档和 GitHub 仓库维护。已完成的语音入站、图片保存及两次转发负例见[E151](../../docs/151-native-voice-and-image-saving.md)。程序主动创建聊天语音条仍缺官方普通账号入口；WAV 原件可收发、下载和播放。语音出站已暂缓，不影响适配器开发。

继续工作只依据[关键路径](CRITICAL_PATH.md)的新入口或实际缺口，准确版本/错误/能力在[总览](../../docs/102-user-requirements-and-roadmap.md)。主Agent统管现场和GitHub，子Agent只在隔离/tmp实现及离线审查；无聊天心跳。原范围和禁令见[AGENTS](../../AGENTS.md)。
