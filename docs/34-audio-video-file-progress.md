# 音视频原件：私聊 WAV 出站首格

2026-11-11 21:19。图片功能提交 `c090085` 后继续下一段，已完成 liev→veil 私聊 WAV 文件的真实客户端下载和系统播放器打开。**这只完成 WAV/MP4 八格文件矩阵中的一格，不是原生语音条通过。**

固定官方 v1.0.67 的[发送实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/chat.go)在 `file/audio/video` 分支把服务端类型统一设为 `file`，Help 也明确 audio/video 是文件语义别名。因此本次直接使用 bridge `file` 入口；没有把改一个 flag 当成原生音视频实现，没有修改这一官方映射。

实验 `DAB-MATRIX-20261111-direct-wav`：已持久确认，历史和客户端都呈现文件；veil 在钉钉点击下载并保存到本机，`direct-received.wav` 与 fixture 逐字节一致（32044 B），资源下载原件也相同。随后在 Finder Quick Look 打开此实际下载文件，音频播放器显示时长 0:01、播放进度到 00:01；独立 WAV 解析确认单声道、16000 Hz、16000 帧。没有以工具无报错声称听觉质量通过。

原始证据、资源及客户端文件留在 `local/audio-video-ui-20261111/`。下载后前台曾切回旧聊天搜索窗口，该截图只说明窗口焦点变化，不当作音频已打开；最终通过 Finder 的实际播放器确认。

只读复核：`python3 scripts/accept_wav_direct.py`；[脱敏证据](../evidence/2026-11-11/wav-direct-file-ledger.json)。已确认实验不再发送。`media_matrix_probe.py` 新增 WAV/MP4 文件案例，MP4 本轮只预览、未发送。

下一步先用 veil UI 上传 WAV 到 liev 私聊、验证实际任务处理，再补私聊 MP4 双向及客户端下载打开；原群增加第三人的范围问题仍待答复，不等待该项开展私聊工作。原生语音/视频须另有官方服务契约、可调用入口与 UI 实测，当前明确未通过。
