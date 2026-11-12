# 采用CEO发送凭据负例：拒绝冲突与错任务状态

2026-11-12，E102。沿用CEO固定`92e360ed`的[发送验证器](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/dws_client.py#L3814)及[负例](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_dingtalk_delivery_verification.py)，对照本项目接缝。不是复制整套业务服务或重做发件箱；新增校验与unittest为本项目编写，上游文件只读核摘要，不运行其服务/测试。

## 官方边界和真实缺口

固定官方源码`63a7c490`的[send_status.go](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/shortcut/chatmsg/send_status.go)展示：DWS保留底层响应，另投影sendReceipt、openTaskId、messageRef；沿result/data/response/content/message查找第一个标识。状态投影会优先使用响应中的task ID，没有才使用请求ID。这个设计不会替bridge核“是否属于本次持久发送”或发现所有冲突。

本项目旧代码已避免引用源/nextActions递归取ID，必须查询sendStatus且核会话，也有原key幂等及终态竞态保护。但仍有明确缺口：只读投影task、忽略底层矛盾；状态响应task与持久task不比对；部分非法/冲突message ID可被当成功；引用源ID若被投影成新消息，也未拒绝。合成回归在冻结E099旧产品上执行8个方法，22个失败子场景，原日志保留。它证明本地校验缺口，不表示真实平台已返回这些错误或现场曾错投。

## 窄修复与对照

| CEO参考负例 | 本项目处理 |
|---|---|
| 投影与原始发送task冲突 | 只遍历官方响应wrapper；唯一一致task才入submitted。没有task或冲突保持outcome_unknown，不查询猜测ID |
| 状态属于另一task | 确认/失败前核返回task与持久task；不一致不将本次标confirmed或failed |
| 输出ID非法/冲突/另一会话 | 核messageRef类型、非空及底层ID一致性；保持未知或原pending记录 |
| 引用旧消息与操作建议ID | 不遍历referencedMessage、nextActions、metadata；新消息ID不得等于本次引用源 |
| accepted、PENDING、普通成功文字 | 都不是送达；仍只认可本次状态查询的SUCCESS及有效消息/会话 |
| 明确嵌套失败或其他契约 | 拒绝把其task当接受成功；已存在不确定操作不重做 |
| 重启、终态竞态 | 原key不重发，保留已有终态保护；E052原并发回归继续覆盖 |

无契约版本字段的历史合成/兼容响应保持原支持；若明确声明其他版本则拒绝。没有凭据修复、自动换账号/runtime、按相似历史正文推定成功或扩大白名单。当前实现并未建立跨所有路由的全局task唯一性索引；绑定校验针对本次请求及其返回，不声称覆盖恶意提供方伪造全部一致字段。

## 验证与部署状态

8个新增方法先在旧冻结产品上失败，再验证修复；全量使用独立冻结源码和同一新wheel，在Python3.14与3.11安装环境核对，结果见[冻结报告](../evidence/2026-11-12/send-evidence-contract-validation.json)。不会拿HEAD替换已测试代码，也不把离线负例当新增UI。

本记录的初始提交尚未部署：线上transport仍E093，两gateway为E099。后续只在无未终态任务/投递且冻结摘要一致时，用管理器重载受影响transport，保留原账本与gateway；再做唯一合成群任务的真实UI正向验收。原24h观察已经结束，维护另留新记录，不改E101原run及错误。

## E103：已部署并通过真实UI

E102代码提交`3fa5011`后，先核任务/投递全部终态及21模块冻结摘要，再由原manager只重载transport；两个gateway进程、全部旧任务/发件箱/投递/session和配置保持。没有auth/doctor/钥匙串操作，不改E101原观察。维护证据单独留local/send-evidence-deploy-20261112。

veil在唯一AIC群原生输入一条独立任务，Kimi实际Python计算73×19=1387；liev确认与结果两条气泡及AI标识真实可见。两个不同task/message回执与传输账本逐项一致，原key未重放。两路history均在维护后完整同步且poll_error为空。[15项只读核验](../evidence/2026-11-12/send-evidence-deployment-validation.json)通过，UI观察保留本聊天工具记录；没有新增能力矩阵格。

首版审计误猜health存在last_complete_sync_ms而失败，实际字段为last_sync.at/complete；原失败报告留local，修正按真实契约核维护后时间与complete，未重发任务。E102离线报告deployed=false保留初始冻结检查点，当前部署事实以E103为准。下一段C03能力/终态和C04会话兼容性，项目仍未完整验收。
