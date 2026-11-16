# E044：合成语音经官方听记分析并从私聊交付

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，固定官方 DWS v1.0.67、既有 liev profile；产品仍为 E041，无部署或权限变更。此项补 R15 的代表性听记分析任务，不改变 R06 原生语音条、独立 video 或群媒体的未通过判定。

## 实际输入与执行

系统 Tingting TTS 按仓库合成原稿生成 WAV，ffmpeg 转为单声道 16kHz PCM16，21.929938 秒、701836B；没有采集麦克风或真实会议。fixture SHA-256：49300778ccbd5ba9763c55495b39de4be74f77a68feb21d0a00d6d25cd12e7bf。

veil 从原生客户端先发送准备任务，liev 明确回复准备接收且没有调用工具；随后 Finder 复制音频，粘贴到两人私聊，立即上传为普通文件消息。提示没有包含原稿、项目名或关键数字。bridge 下载缓存、runtime 输入与 fixture 同字节。两任务复用同一 native session。

Kimi 实际读取宿主官方工具上下文及 help。一次 `--dry-run` 仅返回 executed=false（其语言参数写为“中文”不能据此宣称被服务端接受）；正式调用写唯一意图后，只执行一次 `minutes +upload-and-analyze --input-language zh --artifacts transcript,summary,todos --wait-timeout 180`。显式 profile、标题和原音频绑定；不发消息卡片、不分享、不改权限、不录制、不创建独立会议。

正式上传和分析成功后，使用原 taskUuid 单独执行 `minutes +detail --artifacts basic,summary,keywords,transcript,todos`。taskUuid、标题、逐字稿、摘要和行动项在两次回执中对应一致，detail 完整且 failureCount=0。创建对象保留；本次没有超时恢复实证，不能将成功路径外推为所有失败恢复均通过。

## 用户端结果与内容核验

官方逐字稿保留三项任务及顺序：周五前完成初稿、核对703元预算、检查5份样本，先完成草稿再复核预算。与合成原稿比较仅数字书写和句号/逗号不同，没有关键事实偏差。服务端还返回摘要及三条行动项；关键词返回空列表，报告明确指出而未补猜。行动项是听记产物，未验证独立待办指派、接收或完成。

liev 完整结论在 veil 私聊界面可见，显示“通过AI发送”。2125B TXT 报告由钉钉 Save 面板下载到本地，Finder Quick Look 打开并滚动到尾部，逐字稿、摘要、行动项及空关键词说明均已检查。runtime export、outbox 暂存、官方 IM 资源下载和客户端下载件同字节；报告 SHA-256：416afde7e2829f1bbfc96ae3a946ec35e3710068299f3f4edebbad722a1ebdb6。账号、taskUuid、原始回执、签名地址没有回传到报告或共享证据。

`scripts/accept_minutes_ui.py` 只读51项通过；5个内存负向分别拒绝错误 taskUuid、额外卡片、错误预算转写、缺失服务端行动项及篡改客户端下载报告。共享证据为 minutes-ui-ledger.json、minutes-audit-negative.json；原始回执、UI、日志和下载件只在 local/minutes-ui-20261112。

新增两任务五确认，DM55/139（138确认1旧拒绝）/148/204；群3/7/12/76、旧任务/投递/日志保持，无自回复触发。原观察1229样本10.243h、6不可达，历史3poll_error和维护保持；尚未满24h。

## 官方与自研边界

上传、ASR、摘要/行动项生成及按 taskUuid 取回均由官方 DWS 承担。bridge 负责授权路由、文件原件、会话/任务和同会话交付；没有重造听记接口。分析失败可能已经创建对象，未来若回执不明需保留原意图与ID，只读对账或用官方 resume-id 等待，禁止改标题重传。

固定版来源：[听记组合事务](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/minutes/workflows.go)、[中文语言示例](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/shortcut/minutes/alignment.go)。官方文件能力与原生语音条分别验收；本次没有播放合成音频评判听觉质量，也没有在 veil 账号内打开 liev 的听记办公页面。
