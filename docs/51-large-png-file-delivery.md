# 超2MiB PNG 文件交付与模型摘要错误

2026-11-12，E032。veil原生私聊一次任务，Kimi实际用Python/Pillow生成1024×1024 RGB PNG，像素来自`random.Random(29).randbytes(1024*1024*3)`，`compress_level=0`。文件3,147,861字节，超过原生image的2MiB上限，gateway按既有规则选择官方file投递，未压缩/缩小、未调用图片上传补充。

四条回复全部confirmed（ack、文字、PNG文件、TXT报告）。钉钉把PNG文件显示为带“文件”标签的图片，可打开独立查看器；不是只能显示无预览卡片。查看器下载原件后Finder Quick Look实际打开，1024×1024像素逐字节与独立重建seed=29相同。export、bridge staged、官方资源下载、客户端下载件字节一致。198B报告也从聊天卡片下载、Quick Look打开，完整SHA/尺寸/字节数正确。

| 对象 | 字节 | SHA-256 |
|---|---:|---|
| PNG原件 | 3147861 | `b83c6fc39b318b21d2d0d3253efe25f3b182253e23ca15ec036623f4b6132d6a` |
| 报告TXT | 198 | `3c40ae39d4ffe9a0766f017f251e7d36a8eacb92894c84c552569faa90ce93b5` |

**发现模型输出错误**：Kimi短回复把SHA截断成了错误前缀，虽然工具实际输出、报告和下载件中的完整SHA正确，仍不能将整项任务标为内容全正确。原短回复、runtime日志、投递均保留；尚未发送更正消息。`file_delivery_passed=true`，但`task_fully_correct=false`、`model_short_sha_correct=false`。下一步对既有产物发一个新的只读校验任务，明确更正，不重跑生成/重发原文件或修改旧结果。

复核`python3 scripts/accept_large_png_ui.py`：28项文件/身份/保持/UI证据检查通过，两负向注入（缺官方资源、损坏下载字节）均拒绝。退出0只表示文件交付范围通过，报告单独保留任务文字错误。共享证据为large-png-ui-ledger.json、large-png-audit-validation.json；截图/原始聊天/日志/下载件只在`local/large-png-ui-20261112/`。

初次报告AX仅busy加载态，截图已显示正确全文；审计未因此放宽，重新打开已有下载件、取得加载后的全文AX再通过。Finder动作超时后先重绑定观察，不重发任务或重复下载。

DM42任务/105outbox（104确认1旧拒绝）/114传输/157事件；群3/7/12/76不变。旧账本/日志/native session逐项保持，无产品代码/配置/部署修改。E030的139全量及E031新增11项工具测试版本保持。该样本证明私聊出站大PNG的file路径，不能外推大图入站/群、20MiB极限或独立image上限扩大。原24h观察继续，未标项目完成。

后续E033见[docs/52](52-sha-correction-ui.md)：只读跟进第一次误判也已保留，第二明确源文本比较后在原生UI更正；不改变本段原任务错误结论。
