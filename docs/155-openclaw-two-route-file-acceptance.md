# E155 · 原生OpenClaw双路文件验收

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


E155 双路文件验收通过：群聊采用全新独立的商品目录颜色筛选任务，私聊按其真实文件接收证明核定；两路collector的modelAndTransportPassed与accepted均为true。客户端文件分别核对字节、SHA-256及唯一名称，公开记录只保留摘要和长度。

E154旧43出库单的未知投递与附件未提交仍保留当时事实；新筛色任务不是重试，不关闭旧原键，也不补造旧任务交付。

两路都由 OpenClaw 调用真实 Qwen3-14B 读取入站原件并写出结果。钉钉收件端全文与宿主发出的正文逐字一致，bridge 添加的前缀和任务号均未出现。钉钉在气泡外显示的“通过 AI 发送”是客户端身份标识。

| 路由 | 客户端文件字节数 | SHA-256 |
|---|---:|---|
| 群聊 | 11 | `27fbd594b79cde22c91cf638e187f726fcd916d05e354b35edcc74620e5497bb` |
| 私聊 | 9 | `32f19951669a9d7c38db85b5ee0a075e6111621784cb9ee6af39b867281a8ee8` |

新群任务仅做商品目录颜色筛选，使用未占用的唯一输出名。原聊天、匹配代码、测试随机标识、原文件名、路径、账号与截图不公开；报告只留两路已验文件摘要和长度。

双路文件验收已满足，可进入[PR #9](https://github.com/veil-chow-fyaic/dingtalk-agent-bridge/pull/9)的合并检查；是否已合并以实际GitHub回执为准。部署收据尚待单独取得，不由本次验收推定正式部署。

真实多轮续接、取消和重启分别验收，E153合成范围不升级；原R06与全部产品完成状态不改。 不重写E154失败/未知，也不把此次接收证明外推为零故障。

[脱敏收据](../evidence/2026-11-19/openclaw-two-route-file-acceptance.json) · [E154保留记录](154-openclaw-real-files-and-client-receipts.md) · [插件使用](../integrations/openclaw-channel/README.md)。
