# E041：附件原始名称与Unicode CSV实际处理

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12。原先 gateway 只向 runtime 传整理后的本地路径：文件名中的空格、emoji等变成下划线，模型无法准确报告原始附件名。现在另外传JSON元数据：原始名、类型、字节数、SHA-256和安全本地路径；缺失原名为null，不将缓存名伪称原名。原始名称明确作为数据，不改变执行权限、路径校验或输出文件命名策略。

新增回归先因缺少元数据而失败，修复后验证带引号/路径样式/emoji的名称仍保真，本地文件保持在inputs内且字节一致；无原名图片保持null。Python3.14全量163项、Python3.12受影响gateway34项通过；E040另有3.12完整162项，不混称本轮双版本163全量。新wheel六入口/18模块通过，两个空闲gateway已加载，传输和原观察不重启。

## 实际用户过程

veil原生私聊先发DAB-UTF8-20261112-001准备任务，只要求等待下一份CSV。该提示没有给出文件名、数据或答案。liev回复准备接收；此任务没有工具调用和产物。然后Finder选中唯一合成文件`订单 明细🧾-DAB-UTF8-041.csv`，复制到钉钉输入框，客户端立即作为独立文件消息上传。它是第二个任务，不是自动合批或单消息多附件。

原件135B、UTF-8 BOM，包含逗号项目名、带引号项目名、字段内LF、空字段、中文和emoji。官方下载缓存与Kimi输入保持原始字节；实际本地名经安全整理，原名另由元数据提供。Kimi两次Bash实际读取文件，用csv与Decimal解析计算，生成CSV和JSON。

| 验证对象 | 现场结果 |
|---|---|
| 三行计算 | 3×12.50=37.50；4×0.75=3.00；2×8.25=16.50；总计57.00 |
| 原始文件名 | liev完整短回复及JSON中空格、中文、🧾均正确；不是从用户文字照抄 |
| CSV175B | 原生文件卡片下载、Finder Quick Look打开为表格，字段/金额/TOTAL可见 |
| JSON572B | 原生下载、Quick Look打开完整正文，原名、编码、3行、57.00与所有明细正确 |
| 字段内换行 | 文件解析后保留LF；Quick Look表格把它显示为同一单元格中的空格，视觉表现与原件分层记录 |
| 原件与输出 | fixture/cache/runtime原件相同；两份exports、outbox暂存、官方资源与客户端下载件各自同字节 |
| 状态 | 两个任务、六条确认回复；同native session，无自回声；旧记录/日志和群账本保持 |

DM50任务127outbox（126确认1旧拒绝）136传输187事件；群3/7/12/76。原观察1150样本9.584h、6不可达，历史3poll_error和维护保留，未满24h。没有新的群、引用、原生语音或单消息多文件通过结论；E039 manager历史错误未因本轮正常重载被改为已解决。

## 可复核证据

`python3 scripts/accept_unicode_csv_ui.py`只读核验48项。4个负向注入拒绝错误原名、被扁平化的CSV换行、丢失空字段及缺少官方资源，未修改真实证据。

共享：attachment-metadata-install.json、attachment-metadata-validation.json、unicode-csv-ui-ledger.json、unicode-csv-audit-negative.json；合成fixture可入Git。账号、AX/截图、下载件、账本、模型日志在local/unicode-csv-ui-20261112。

下一独立恢复项：真实Kimi工具执行中只停止私聊gateway，验证同组工具停止、重启后一次取消反馈、不重做任务及后续任务可继续。沿用原传输和24h观察；未知投递仍按原key对账。
