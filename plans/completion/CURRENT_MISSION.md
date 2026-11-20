# 当前任务

E168 八项审查修复已验证，公开源码 `907e8e4`，插件 0.2.6。原测试群的新文件由独立本地模型完成，客户端下载件逐字节一致。原组织宿主最近一次已验证安装为 E166 的 0.2.5，验收开始时原端口无监听，结束时原 gateway 端口重新可连接，原微信容器作业当时未加载。 [E168 文件验收与回归](../../evidence/2026-11-20/im-review-fixes.json)

本阶段已交付普通账号 IM 与组织 OpenClaw 的群聊、私聊试用。E167 新盘点表任务已从钉钉收件端下载并复算。现行部署沿用 E166，原生语音出站暂缓。 [E167 收件验收](../../evidence/2026-11-19/stage-delivery-inventory.json)

普通账号 IM 的 CLI、HTTP 和持久 consumer 独立工作。E160 在已验完整回切后，把原授权群、私聊交回同一组织 OpenClaw；两个宿主会话均已续接并正确回复。 [当前运行归属](HANDOFF.md)

主线的双路文件与独立会话已实测。E164 将原发送者已叫停的一笔旧输入保留在退役账本，完成两路回切并重新接管；后续新查询仍可正常执行。保留原输入和独立的 E154 旧发送键。 [E160 现场与测试收据](../../evidence/2026-11-19/openclaw-resident-reentry-and-cancel.json)

Hermes 与 DeepSeek Harness 的 ACP 接入后续分别验证。R06 普通账号原生语音条出站按用户意见暂缓，日常音频交付可用 WAV 原件。 [任务池](TODO.md) · [验收范围](../../docs/102-user-requirements-and-roadmap.md) · [现场约定](../../AGENTS.md)
