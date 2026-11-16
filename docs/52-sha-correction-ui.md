# 错误摘要的只读复核与明确更正

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E033。原E032大PNG交付成功，但Kimi短回复的SHA前缀错误；旧任务继续保持`task_fully_correct=false`。本段未重新生成或回传文件，未改旧消息、结果或账本。

veil原生私聊先发送一次只读核验任务。Kimi实际Read报告、Bash/Python重算PNG，输出正确完整SHA和3147861字节，却回复“只读核验一致，无需更正”。原生客户端可见完整错误结论。因此该任务在执行账本为completed，但语义验收失败；两种状态不混用，也不把完整SHA正确当作结论正确。

随后只发送一次不同内容的新任务，把E032错误短回复原文直接提供给Kimi，要求Python从原文提取省略号前的前缀并用`startswith`比较。真实工具输出`prefix_match=False`、`report_sha_match=True`、`report_bytes_match=True`。最终liev回复明确说之前“无需更正”不正确，并给出完整SHA与字节数；veil主聊天的全文AX及截图均已核对。这是补充明确源文本后的新任务，不是未知投递重试。

完整SHA：`b83c6fc39b318b21d2d0d3253efe25f3b182253e23ca15ec036623f4b6132d6a`。两个只读任务各有ack和文字回复，共4确认投递，无artifacts。既有15个exports的文件集合、字节、SHA和mtime逐项不变；旧任务/投递/运行日志保持，同一native session。DM44任务109outbox（108确认1旧拒绝）118传输163事件；群3/7/12/76保持，无部署或产品改动。

复核：`python3 scripts/accept_sha_correction_ui.py`，37项只读检查通过；篡改最终结论或runtime日志摘要两种负向注入均拒绝。共享证据`evidence/2026-11-12/sha-correction-ui-ledger.json`与`sha-correction-audit-negative.json`。原始UI、聊天和两次运行日志索引仅保存在`local/sha-correction-ui-20261112/`。

`original_task_fully_correct=false`、`first_followup_semantically_correct=false`继续保留，只有明确源文本的更正通过。此结果不保证模型今后不会误述摘要；bridge的文件摘要是确定性证据，模型文字与传输成功必须分别验证。原24h观察不重置；项目未完成。
