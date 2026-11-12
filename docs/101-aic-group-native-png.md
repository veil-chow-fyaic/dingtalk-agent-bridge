# E096：AIC测试群原生PNG出站与下载打开

沿用E095的精确AIC新群和普通账号身份，veil在原生钉钉界面发送唯一 `/agent [AIC-E096-PNG]` 任务，要求实际用Python Pillow生成640×360白底、蓝色21/橙色22两根柱子的合成图，并将原件交回本群。没有重做旧图片实验或向企业群发送。

Kimi实际调用Bash/Python/Pillow，生成4762B PNG，再用ReadMediaFile检查。任务completed，三个outbox均confirmed；宿主投递payload是image且绑定原定SHA，不是Markdown图片链接或普通文件降级。产品沿用E093冻结模块，无代码改动/全量测试重跑。

原生UI实际观察：liev(liev)和“通过AI发送”、群图片气泡；点击后独立图片查看器显示“liev分享的图片 5KB”，画面可见AIC-E096-PNG、21、22、TOTAL43和两根柱子。点击下载图标，保存到 `local/aic-png-20261112/aic-e096-client.png`，界面提示下载成功；在Finder快速查看中打开该下载件，图像预览和文字标记再次确认。

[九项只读核验](../evidence/2026-11-12/aic-group-png-validation.json)全部通过：完成/三个confirmed、image类型、预定SHA、下载字节一致、PNG签名/640×360、Python/Pillow和读图工具调用。下载SHA256为 `e8cc5413642ea555574090133bfb4ceefd74dfa60a788384185b31a2d4a7ba4d`，与Agent产物及投递原定SHA完全一致。原件、执行事件、完整任务/回执只留local；UI事实为本聊天CUA观察，自动检查不伪装UI检查。

UI控制中遇到两次30秒工具超时及一次查看器0尺寸截图错误，均先重新读取窗口确认已完成的动作，没有重发任务或换key。保存对话框paste路径未生效、快捷键全选未生效，使用已观察到的PathTextField输入ASCII路径及setValue设置文件名后确认保存；没有修改系统设置。最终Quick Look虽然一次捕获超时，重新连接确认预览实际已打开。

群PNG出站格由部分/blocked改为通过E096；当前41/64通过、22blocked、1部分，14 MUST仍8项不完整。仅此一份小PNG出站样本，不外推JPEG、音视频、原生语音/独立video或长期稳定。下一段在同一AIC群补JPEG/WAV/MP4和群长文/控制；原企业群禁测、旧失败/24h维护保留。
