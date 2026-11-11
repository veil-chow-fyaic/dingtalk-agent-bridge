# 双账号媒体与真实事件：2026-11-11第二轮

本轮延续用户授权：客户端veil作为用户，DWS显式liev profile，原内部两人群及两者私聊。没有创建bot、邀请成员或扩大监听范围。任务目标与剩余工作见[活动计划](../plans/completion/INIT.md)，此前TXT/CSV、上下文和重启基线见[docs/27](27-two-account-ui-acceptance.md)。

## 已实际做的事情

在钉钉输入框发出两个事件标记；从Finder复制合成PNG/PDF到钉钉群和私聊；liev通过bridge的HTTP发送图片与PDF，稳定幂等键使用`DAB-MATRIX-20261111-{group|direct}-{png|pdf}`。没有用回读API代替veil的UI输入。

| 路径 | 图片与PDF传输 | 用户界面 | 文件核验 |
|---|---|---|---|
| veil→liev 群 | 两条分别收到 | veil原生图片气泡、PDF上传完成；无命令不执行 | PNG两资源和PDF原件一致 |
| liev→veil 群 | 两条confirmed | liev左侧图片、PDF卡片/预览、“通过AI发送” | bridge下载一致；本轮未另下载群PDF；19:15续跑已下载打开并校验，见docs/29 |
| veil→liev 私聊 | 两条分别收到 | veil原生图片、PDF上传；PDF触发真实Kimi识别并返回TXT | PNG两资源和PDF原件一致 |
| liev→veil 私聊 | 两条confirmed | liev图片/文件消息；PDF客户端下载为direct-received.pdf，Finder Quick Look打开 | PDF客户端下载摘要一致；图片的完整客户端另存待补 |

PNG 1853字节，SHA-256 `14bc34d2e2aed2a70b0371def3f39f8c8dc344c3bf998229c7cb83893781c582`；PDF 3081字节，SHA-256 `8e327441f34a2eee785cb4b211705da7f368c14d9f808503a0c0fa4ea9aba7bf`。8个传输案例共10份资源（真人原生PNG各有两种ID），全部匹配合成fixture。没有将UI截图像素当作原件摘要。

客户端行为：PNG粘贴进入草稿后需发送；PDF粘贴启动上传，群里同名文件会弹出新增/覆盖，本轮选择新增。UI显示的`(1)/(2)`名称可能与DWS历史名称不同，核对使用消息身份、资源和摘要。PDF默认关联Chrome，本轮实际打开验证采用Finder Quick Look，可见“DAB MEDIA TEST 20261111”。私聊任务已回复仍可显示原消息未读，不能将DWS读取当成已读回执。

## 真实UI暴露并修复的缺陷

真人原生PNG的DWS历史同时包含正文中的mediaId和额外`contentType=image`资源ID。旧解析器将后者标为`unpositioned_resources`，第一条私聊图片任务进入blocked；DWS自身发出的图片只有一个引用，过去自发自读未覆盖这个差异。

本轮分别下载两份资源，确认SHA和字节相同。实现现在保留候选别名，下载与完整性校验后，仅当它和已定位图片的SHA一致才认作别名；缺失资源、摘要错误或不同图片仍不交给runtime。没有把所有额外图片静默丢弃，也没有猜测未知图文顺序。

重启两个gateway后从UI发送新的图文任务：私聊图片在正文前，群聊`/agent`正文在图片前。`DAB-MATRIX-IMAGE-FIX-001`、`DAB-MATRIX-IMAGE-GROUP-002`均只执行一次，Kimi读图并返回“DAB MEDIA TEST 20261111”、320×180，veil界面已核对。图文消息的资源引用实际只有一个，因此另于19:11从veil UI重发纯PNG；新的纯图任务确有两个资源引用，记录1个verified别名，完成识别并在liev回复中返回正确文字和320×180，确认真正走到本次修复路径。原blocked保留作失败审计；没有修改旧任务为成功或静默重放。后续显式重试/恢复体验仍在C03中。

## Stream业务采样与边界

`scripts/capture_route_events.py --seconds 600 --run-id ui-matrix-20261111`启动两个有界官方用户事件订阅（群/o2o，精确目标与profile，flatten NDJSON）。原始记录只放local。实际收到群5、私聊11个事件，16个消息ID全部在持久history账本中找到，每路无重复、0 rejected；两进程正常退出0。

真实字段包括type、event_id、timestamp、subscribe_id、message_id、conversation_id、sender、sender_open_dingtalk_id、content、create_time、event_time。现有字段适配能接受实际业务。事件时间到本机观察时间样本为群0.551–0.771秒、私聊0.434–0.819秒；这是跨时钟样本，未经时钟校准，不能当端到端回复SLA，也不是事件到history可查的延迟。

**本轮19:05时常驻服务仍为15秒history轮询；后续已启用Stream并完成唤醒/补漏，见[docs/29](29-stream-service-and-offline-recovery.md)。**此次独立订阅验证实际事件供给；唤醒集成、断线恢复、24小时长期行为继续待测。health已移除固定`skipped_by_user`状态，改报账本中明确`from_self=false`的实际数量；未知身份不会计入，health不自称UI验收。

## 可复核资料与版本管理

- [只读媒体/事件/任务审计结果](../evidence/2026-11-11/media-matrix-ledger.json)，复核命令`python3 scripts/accept_media_matrix.py`，不发送或执行任务。
- [人工UI观察台账](../evidence/2026-11-11/media-matrix-ui-observations.json)。原始截图、AX、消息ID和下载明细仅在`local/ui-matrix-20261111`，事件原文在`local/event-captures/ui-matrix-20261111`。
- [自动测试结果](../evidence/2026-11-11/scenario-regression.json)：76项。新增图片别名相同/不同/缺失资源防护，及health未知身份排除、Git暂存秘密测试。自动测试不替代上表UI观察。
- Git分支`codex/complete-bridge`；基线`166b11b`、标签`baseline/ui-2026-11-11`；没有远程发布。提交钩子扫描暂存blob中的当前已知账号/会话ID、HTTP令牌、私密路径和私钥模式，再检查公开handoff。它不是覆盖一切未知秘密的检测器。

本轮仍未完成DOCX/XLSX/ZIP/WAV/MP4的完整双账号UI矩阵、出站所有媒体逐个客户端下载、原生音视频、服务Stream/断连、可安装交付、办公接入和24小时观察。它们继续由同一长任务执行，不能用此次通过抵消这些空格。
