# 独立图片与 Markdown 内联图的客户端差异

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-11 20:23–20:36，补查此前已确认投递的私聊PNG，没有重放原来的固定实验。

当前bridge的`image`字段在`core.py`中调用DWS `+messages-send --markdown`，生成内联图。旧图在veil客户端可见，但本轮点击、双击和右键未打开图片查看器或保存菜单；聊天记录的“图片”页按liev筛选为空。同一客户端中，veil此前发送的原生PNG双击立即打开查看器并显示下载按钮。这里只说明本次客户端路径，不断言所有版本均无法保存内联图；也不能把旧图可见外推为原生图片功能完整。

本机固定v1.0.67的[Shortcut Help](../evidence/2026-11-11/messages-send-help.txt)与[原子命令Help](../evidence/2026-11-11/v67-chat-message-send-help.txt)明确已有独立图片入口：`--as user --msg-type image --media-id <已有资源>`。因此优先用官方路径，无需AX代发或新建bot。

## 独立实验结果

先确认旧Markdown投递为confirmed，取同一liev profile下已核实的合成PNG资源。新实验专门比较消息类型，稳定key=`DAB-NATIVE-PNG-20261111-direct-001`。先dry-run核对`msgType=image`，再独占创建本地intent并只发送一次，保留task/status；这不是未知投递重试。没有更换发送身份。

结果：官方状态SUCCESS，history中恰好一条新消息，发送者为liev、无自身任务。veil界面出现独立图片气泡，双击打开“liev分享的图片”查看器，点击下载后显示“下载成功”。从“打开文件夹”进入Finder，再Quick Look打开实际下载文件，图中合成文字正确。

客户端下载`direct-received.png`为1853字节，SHA-256 `14bc34d2e2aed2a70b0371def3f39f8c8dc344c3bf998229c7cb83893781c582`，与fixture逐字节相同。Finder观察有一次CUA超时，重连后确认预览已打开，没有重复发送或重复下载。

只读复核：`python3 scripts/accept_native_image.py`。见[账本](../evidence/2026-11-11/native-image-direct-ledger.json)及[UI观察](../evidence/2026-11-11/native-image-ui-observations.json)。原始回执/资源ID/截图只留`local/native-png-20261111`，旧内联图尝试及真人原图对照只留`local/ui-matrix-20261111`。

## 尚未完成的接入工作

本轮证明的是官方独立图片发送及私聊用户获取原件。**bridge仍走原Markdown图片路径，尚未修复**；群聊独立图片也未测。下一轮先查官方本地图片上传获取mediaId的适用入口，再补持久上传/发送阶段与失败对账，保留原幂等账本；不要先发Markdown再自动补发原生图。群/私聊原生图片都须通过UI下载打开后，才能将产品图片交付标完整。原生音视频/引用多附件等后续项仍在活动计划中。
