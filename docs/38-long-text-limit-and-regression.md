# 长文实际失败、UTF-16 分段修复与证据边界

后续状态：原unknown已由[E019](39-rejection-reconciliation-and-feedback.md)按官方绑定日志对账为rejected，原行完整存入审计表；本文描述E018发现/修复时的冻结证据，失败正文仍未重发。

2026-11-11，veil 原生钉钉 UI 向 liev 私聊交办两个不同内容的长文任务，Kimi 均实际生成文本和文件。首个任务暴露真实投递缺陷：第一段超出官方服务端限制，被拒绝；第二段和文件送达。修复后新任务的两段与文件均 confirmed，两份客户端下载件都在 Quick Look 打开，字节与各自原文一致。完整长聊天气泡尚未逐段目视验收，不能据 API 成功标整项 UI 通过。

## 官方限制与现场事实

最先尝试在客户端粘贴 6942 个 Python 字符，钉钉弹出“粘贴的文本过长，是否转为文档发送到当前会话？”。选择取消，输入框为空，未发送、未自动转文档。这不是通过二分测出的通用长度上限。

随后 3588 字符的消息实际发送，包含60行中文、换行、🙂🚀、标点；入站 history 与 UI 输入逐字符相同。Kimi 写入8039字节原件，返回6825字符答案。旧 gateway 按6000个 Python 字符切分，另加 `[Agent] `，首段6008字符；官方 DWS 日志明确给出：

> Length of filed: 'textContent.text' cannot greater than 5120 but actual is 6220.

同一条日志标记 `send_personal_message`、`invalid_request`、`PARAM_ERROR`。6220与首段UTF-16单位数相等，包含前缀和emoji代理对。不是 UTF-8 字节数限制，也不能把本次普通账号 text 限制外推到 bot、Markdown 或卡片。

首段没有 openTaskId，history没有该正文；原 bridge 把异常保存成 `outcome_unknown`，没有可调用官方状态查询的任务ID。这个原账本和失败快照保持不动，未换key、未重发；后续复验使用不同内容、独立用户任务。官方明确拒绝的证据已归档，但数据库状态尚未形成带证据的终态对账记录，doctor仍会报告未知投递。下一步应补明确拒绝的分类/可审计对账，不能直接把旧记录改为成功。

## 修复与验证

`text_limits.py`按 UTF-16 单位计算5120上限，包含 `[Agent] `；gateway优先按完整行切分，单行过长按Unicode码点边界切开，不切断代理对。offset仍来自原正文，已经持久化的outbox不重新切分、不改key。HTTP/CLI新发送的超限text在调用DWS/预留投递前拒绝；旧key先返回原记录，避免通过新验证重投旧实验。

4项新增回归覆盖精确边界、emoji/中文/CRLF/超长单行/空答复、完整重组、gateway重启不重执行、超限不调用DWS不预留账本，以及旧超限unknown不重发。全量99项通过（14.257秒），不是99次真实钉钉测试。

空闲后维护重启传输和两个gateway，记录在原24h run的maintenance日志。复验输入3592字符，使用新的“修复换行/复验数据/新例完整保留”内容；Kimi返回6844字符，两段分别4893和1967字符，UTF-16为5063和2037，均 confirmed；另有确认回复和结果文件，共4条 confirmed。

## 空白与客户端证据分层

固定官方v1.0.67源码 `internal/shortcut/runner.go:53` 的 `RuntimeContext.Str` 对flag执行 `strings.TrimSpace`，`StrFirst`沿用它。复验第一段尾部一个 LF 被裁掉，history长度4892而待发送payload为4893；第二段完全一致。审计只接受已证实的这一末尾LF差异，明确报告 `historyProjectionByteExact=false`，不吞掉任意空白/文本差异。分段payload能完整重组runtime答案，但不能称官方history字节无损；需要字节精确内容使用文件。

两次文件均从钉钉卡片点击下载，经保存对话框落盘，再用 Finder Quick Look 打开；各为3359字符/8039字节，无额外末尾换行，内容/摘要与对应fixture相同。第二次Quick Look采集调用超时后，重新观察确认文件已经打开；没有再次下载或重发。

本次聊天UI确认了输入、任务接收与结果文件卡片，Quick Look正文含60行中文、emoji、首尾行。点击聊天滚动区+PageUp没有移动内容，AX Scroll Up也没有有效展示历史；两条完整长回复气泡仍待可用浏览路径。引用消息同样未由这些操作证明。没有新增群发送。

## 复核与后续

```bash
python3 scripts/accept_long_text_ui.py
python3 -m unittest discover -s tests -v
```

只读现场审计56项覆盖失败保留、修复后投递、明确LF变换、两个原件和客户端下载件；缺回复、损坏客户端下载件的内存负向检查均失败。原始输入/账号/任务/日志/截图在 `local/long-text-ui-20261111/`；脱敏报告在 `evidence/2026-11-11/long-text-*.json`。

新增2任务/8条outbox，其中7条confirmed、1条原始unknown；两路原32任务/71条Agent投递/84条传输投递逐行保持。当前私聊31任务、72条outbox（71 confirmed/1 unknown）；原历史blocked和cancelled仍在。24h观察器未重置，约3小时27分钟时415样本、1不可用采样，维护已记；不是同版本24h或零中断。下一步优先处理可审计的明确拒绝终态和错误反馈，再继续统一服务管理、引用/长气泡UI、办公能力；全项目未完成。
