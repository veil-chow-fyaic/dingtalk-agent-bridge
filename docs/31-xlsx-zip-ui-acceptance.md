# XLSX / ZIP 双账号文件与实际任务验收

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-11继续同一任务。范围为原两人群及veil/liev私聊；veil使用钉钉原生UI上传，liev通过显式绑定的DWS真人profile发送。没有新增bot、成员或权限。服务与两路Kimi gateway持续运行，本轮没有重启或配置变更。

## 八个传输案例

每种格式均完成群/私聊 × 两个方向，共8个案例、8个下载资源。veil在Finder复制合成文件，粘贴到钉钉上传；群同名提示选择“新增文件”。liev使用已有HTTP接口发送原件，固定key为`DAB-MATRIX-20261111-{group|direct}-{xlsx|zip}`。每个只发送一次，随后只读核对。

| 路径 | XLSX | ZIP |
|---|---|---|
| veil→liev群 | UI上传完成，原件完整；普通文件不触发任务 | UI上传完成，原件完整；普通文件不触发任务 |
| liev→veil群 | UI文件预览可见，客户端下载后Numbers打开 | UI文件卡片可见，客户端下载、系统解包、TextEdit打开文本 |
| veil→liev私聊 | 一个真实Kimi任务，准确提取A1/B1并返回TXT | 一个真实Kimi任务，读取压缩包清单和正文并返回TXT |
| liev→veil私聊 | 单独发送的原件客户端下载后Numbers打开，无自身循环 | 单独发送的原件客户端下载、系统解包、TextEdit打开，无自身循环 |

XLSX为1577字节，SHA-256 `6279bd1d04395f5b8ffa8a7d91f58c28bdea9d3d6453c21b0149bc9a6325cc9c`。单工作表DAB，A1=`DAB-XLSX-001`，B1=`1`。两份客户端原件都在Numbers打开，标记因窄列换行显示，数值正确；未编辑或另存转换。

ZIP为243字节，SHA-256 `97124afc3e59ef52b84b1b4c402dace45c24ea00285cde940db5ecb84dbd8e99`。仅含113字节UTF-8的`dab-file-001.txt`。群/私聊下载到独立目录后通过系统解包，TextEdit实际显示合成标记、中文及ASCII校验行；两个解包文本均与fixture逐字节相同。

四份客户端下载原件与fixture逐字节相同，另8份桥接下载资源也相同。钉钉对同名XLSX显示`(1)/(2)`，校验使用消息身份与内容摘要，不依赖显示名。

## 两个实际文件任务

私聊只上传附件就自动接收任务，未再补一条指令制造第二个任务。每个附件恰好一个completed任务，分别产生接收回执、准确文字答案、TXT文件，共6个confirmed投递；历史确认发送者均为绑定的liev。

用户端实际从钉钉下载并在TextEdit打开：

- `0-dab-office-001-xlsx-content.txt`，82字节，列出A1与B1=1；SHA-256 `74fd0557f19e3f5d8f4682ed402cfbe21c1608030833da36ab6dfb01fca1b270`。
- `0-dab-archive-001-summary.txt`，235字节，包含ZIP清单和完整合成原文；SHA-256 `08eee5e8a0d67a2b8dc9afdb088b4408f6c284336caa31369e1a8b546f83ed42`。

两个客户端下载TXT与实际runtime产物摘要一致。群普通附件没有执行任务，liev自发文件也没有触发任务；这两项是预期策略。

## 可复核证据和限制

`python3 scripts/accept_extended_office_files.py`只读检查已发生的实验，不发送、不重放。73项案例检查和精确8格覆盖通过：[账本](../evidence/2026-11-11/xlsx-zip-ui-ledger.json)。额外用内存注入验证缺资源和客户端下载损坏均不能通过：[审计负向验证](../evidence/2026-11-11/xlsx-zip-audit-validation.json)。缺资源由materialize明确抛出`missing_downloaded_resource`，不把异常吞成通过。

UI观察与账本分开：[13份现场截图的摘要及观察](../evidence/2026-11-11/xlsx-zip-ui-observations.json)。原始截图、AX、下载件、消息身份和冻结账本保留本机`local/office-ui-20261111`，不入Git。群ZIP首次打开后的即时截图尚未显示解包文本，该图不作成功依据；后续实际文本打开才计通过。

样本是基础OOXML和单文件ZIP，不代表公式/宏/复杂版式、加密或嵌套压缩包、恶意解包隔离全部已验。原生音视频、引用/多附件、队列控制、受控办公和完整运行交付继续推进；整个项目未完成。

24h观察run=`reliability-20261111`连续保留。20:20复核PID所属命令正确、状态新鲜、89个样本/约44分钟/0次不可用；这是短期进展，不是24h通过。没有为本轮测试重启观察器，heartbeat `bridge`继续启用。
