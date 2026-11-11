# DOCX四方向与真实24h观察启动

2026-11-11 19:36之后继续同一任务，未等待上段[Stream验收](29-stream-service-and-offline-recovery.md)汇报。范围仍是原群及veil/liev私聊，DWS显式liev真人profile。没有远程发布或成员变更。

## 用户侧文件与任务闭环

veil从Finder复制合成`dab-office-001.docx`，通过钉钉群/私聊输入框上传。群内同名提示选择“新增文件”，不覆盖旧实验。liev通过已有HTTP发送工具回传同一原件，固定幂等key为`DAB-MATRIX-20261111-{group|direct}-docx`；随后只读对账，不重发。

| 路径 | 传输与策略 | 用户获取/执行结果 |
|---|---|---|
| veil→liev群 | DOCX原件收到，普通文件不执行Agent | 群上传完成、文件卡片可见 |
| liev→veil群 | 官方DWS发送confirmed，history与资源相同 | 从钉钉下载`group-received.docx`，TextEdit打开正文正确 |
| veil→liev私聊 | 附件直接触发一个Kimi任务，原件下载完整 | liev回复准确提取的正文，并回传93字节TXT；TXT也通过客户端下载、打开核对 |
| liev→veil私聊 | 同一原件单独发送confirmed，未触发自身循环 | 从钉钉下载`direct-received.docx`，TextEdit打开正文正确 |

合成DOCX为926字节，SHA-256 `e010fdcfa6976a35fd5ac2901f8b31a87afcf7672efa32aeebc8df465de26fb6`。四个下载资源及两份客户端DOCX与原件逐字节相同。内容为“DAB-DOCX-001 synthetic attachment”，是一个真实OOXML单段落样本，不代表复杂版式、宏和任意损坏Office文件全部通过。

私聊任务只执行一次，接收回执、文字结果、TXT结果文件共3个confirmed投递，全部来自绑定的liev账号。客户端取得的TXT与实际runtime输出摘要一致，TextEdit显示提取内容正确。没有让模型重复执行来凑成功证据。

DOCX的Quick Look尝试没有显示正文，保留尝试截图但不作“打开通过”依据；最终采用TextEdit实际打开，未修改文件。钉钉会为同名文件添加`(1)/(2)`，界面名称和发送原名可能不同，因此以消息身份与原件摘要核验。

只读复核：`python3 scripts/accept_office_files.py`，检查已发生的四方向传输、任务、投递及客户端下载文件。见[账本检查](../evidence/2026-11-11/docx-ui-ledger.json)、[UI观察](../evidence/2026-11-11/docx-ui-observations.json)。原始数据保留`local/office-ui-20261111`，不入Git。`media_matrix_probe.py`补充DOCX/XLSX/ZIP白名单，但本轮只实际发送DOCX；XLSX/ZIP预览不能算验收。

## 24h观察已开始，尚未通过

2026-11-11 **19:36:08 +08:00**，基于提交`8f214f4`启动`capture_service_observations.py --seconds 86400 --interval 30 --run-id reliability-20261111`。它是有界、只读的后台观察器，不安装开机自启、不发送探测消息。预计满24h为11月12日19:36后；实际以退出原因、单调时长和采样记录为准。[启动记录](../evidence/2026-11-11/reliability-start.json)明确`passed=false`。

续跑时检查`local/service-observations/reliability-20261111/status.json`、对应PID命令、更新时间和NDJSON。不要仅凭旧`active=true`判断存活，不重启同名run来隐藏中断；遇到进程结束或异常应保留原样记录。期间代码/配置/服务变更需注明，运行时间不等同消息压力覆盖。DOCX这轮7条新事件已进入该观察器，当前无HTTP失败，但仅为短时进展。

下一步仍是XLSX/ZIP四方向、出站图片另存、原生音视频和引用/多附件；用户侧状态/取消/新会话、可安装交付、liev办公工具以及24h最终复核也继续执行。整个项目未完成，heartbeat `bridge`保持启用。
