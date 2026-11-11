# 通用纯文本引用回复及真实私聊UI

2026-11-12，E027。E027：通用CLI/HTTP新增可选reply_to纯文本引用，官方DWS负责原消息/收件人复核，bridge补当前路由已观察源校验与持久幂等。137回归、干净wheel六入口/18模块同摘要、30只读审计/2负向检查通过。liev→veil一次真实私聊引用confirmed，原生UI可见原双图任务、来源发送者、回复及AI标识；未新增runtime任务或Agent outbox。DM40任务97outbox106传输147事件，群3/7/12/76保持。新版三进程已加载、doctor健康；停机曾触发PID保护错误，后独立确认旧进程全部停止再正常启动，原错误保留。原观察823样本6.86h/6不可用，维护已记，未满24h。

## 使用与官方边界

HTTP `POST /v1/send`原有text请求可加`reply_to`，值为所选account_id/conversation_id路由中`/v1/events`已有的message_id。CLI示例中的值都由调用者自己的路由返回，不是固定组织：

```sh
dab --account-id ACCOUNT --conversation-id CONVERSATION send \
  --key stable-quote-key --reply-to SOURCE_MESSAGE_ID --text '已收到该任务'
```

仅纯文本，仍受5120 UTF-16限制；file/image与reply_to组合在上传/预留前拒绝。未提供reply_to的旧payload/fingerprint不变。提供时源消息ID成为fingerprint一部分：同key同源同正文只读回执，不再次调用DWS；变源/变正文报冲突。未知结果重启后仍未知，不自动重发；同key重放优先于新源校验，源历史不可用也不会触发补投。

源必须已收录在本路由，有明确发送者且account/conversation匹配。bridge不因HTTP用户传入外部ID而读取其他会话。官方固定v1.0.67的`chat +messages-reply --as user --group ... --message-id ... --content ... --idempotency-key ... --yes`完成引用；私聊另传精确peer。DWS重新读取源消息，校验唯一ID、会话、发送者，私聊还校验peer映射。无新bot、Thread转换、权限、UI发送后端或私有协议。

固定源码`internal/shortcut/chat/lark_alignment.go`与`reply_extensions.go`显示：群引用回原始MCP响应，私聊引用有sendReceipt。bridge仅在引用响应缺投影回执时，沿官方响应wrapper提取唯一openTaskId/taskId；来源引用字段不参与提取，多个不同taskId保持未知。最终仍通过官方query-send-status核对SUCCESS及当前会话/真实消息ID，提交成功不等于已读。

## 验证

- 新增5项核心边界/恢复测试、1项CLI stdin/路由测试，并扩展真实本地HTTP子进程契约测试；全量137项通过。覆盖源缺失/跨账号/跨会话/缺发送者、引用变化冲突、超时重启与源删除后不重发、私聊双重绑定、群原始/歧义回执等。
- 干净源码导出、独立venv安装新wheel，六入口与18产品模块摘要一致；资料见[安装证据](../evidence/2026-11-12/quote-reply-install.json)、[回归及负向验证](../evidence/2026-11-12/quote-reply-validation.json)。首次构建用不存在的.venv失败，修正为隔离venv/标准pip build isolation后通过；失败记录保留。
- 既有E026源先做官方dry-run，明确willSend=false且会话匹配。新稳定key仅调用一次HTTP发送；confirmed后官方history中的quotedMessage ID/会话/正文/两资源与原源精确一致。veil客户端真实气泡可见原发送者和原任务摘要、完整新正文、“通过AI发送”。AX提供原提示和两个图片占位符；不要求其与history含图片Markdown的原始串完全相同。
- 旧jobs/outbox/deliveries/runtime日志保持；新增只有1传输投递、1自身事件，无runtime/自动回复循环。30项只读审计与引用ID/回复正文破坏两项负向检查通过；[UI审计](../evidence/2026-11-12/quote-reply-ui-ledger.json)。复核`python3 scripts/accept_quote_reply_ui.py`，不再发送。

## 未通过与部署记录

点击引用的AX原文节点返回cannotClickOffscreenElement，一次后停止；气泡呈现已通过，点击跳回原文未通过。veil发起引用和群引用仍未验；群代码仅自动测试，不借私聊通过标群UI完成。gateway未改为自动引用所有回复，reply_to是runtime通用可选工具参数。

空闲维护stop出现“PID changed during shutdown; no further signal sent”，工具按保护规则停止发信号。随后独立status确认三个旧PID均stopped，才正常start新版，三个进程与live doctor健康。未强杀/忽略归属/删除旧状态；目前缺当时变化后的完整进程身份，不能断言该保护错误的根因或已修复。后续管理器独立项应补有界诊断，不能为省错误而放宽PID保护。

原24h观察器run/PID/起点不变，维护采样新增1不可用，累计6；不能宣称零中断同版本24h。原始请求、回执、源ID、AX/截图、安装/测试/管理器日志均仅在local/quote-bridge-20261112。
