# E093：采用社区文件摘要校验，修复排队后原件变更

## 上游选择与依赖

按E092先核Qwen的 `DwsClientLike`、`DwsImMessage`、`messageContent`、`quotedMessageText`、`parseDwsImEvent`。固定[41a3b9f源码](https://github.com/QwenLM/qwen-code/blob/41a3b9f5a6bbaad3c9fa98f341d5ae453b0265a0/packages/channels/dws/src/dws-client.ts)依赖Node进程、`dws-environment`、`dws-event-stream`；stream进一步依赖`@qwen-code/channel-base`。消息接口保留正文和引用文字，没有本项目有序附件/引用来源/原件摘要的等价契约。当前bridge通过官方history稳定text/resourceRefs投影保留这些信息，不将其替换为较窄的模型，也不混用Stream描述与完整原件。

随后检查社区[CEO Agent Service的DingTalkFileHandler](https://github.com/callzhang/ceo-agent-service/blob/bd3de36b136abfd5e3dc571347358ea5b1be69c1/app/dingtalk_file_delivery.py)及[专项测试](https://github.com/callzhang/ceo-agent-service/blob/bd3de36b136abfd5e3dc571347358ea5b1be69c1/tests/test_dingtalk_file_delivery.py)。其完整类依赖`ProposedAction`、`ActionOutcome`、task artifact目录、业务store和DWS client，不能直接放进通用bridge；但“核对原定SHA256后才发送”的门槛独立可移植。

本次改造这一摘要校验逻辑，接入既有Python发送/账本，不引入CEO业务store、授权审批、登录恢复或新的runtime。原[MIT版权及许可证](../../dingtalk_bridge/licenses/ceo-agent-service.txt)按字节保留，随wheel打包。代码注释记录源commit及改造位置；上游源码快照不改。本项目新回归测试覆盖上游思路在本项目接缝中的行为，未冒称执行了上游整套测试。

## 已复现的问题和修复

旧gateway在任务完成时记录产物SHA256，但出站队列只保存路径。文件在排队/重启期间变化后，bridge会读取当前字节并当作任务结果发送。旧版本合成回归实际得到`confirmed`，预期应拒绝，失败证据保留。

现在任务输出的file/image携带`expected_sha256`。CLI增加`--expected-sha256`，HTTP/Python接口提供同名字段；小写64位hex，仅适用于file/image。bridge对即将冻结的同一份字节核摘要，不一致时返回HTTP409 `artifact_integrity_mismatch` / `delivery_attempted:false`，本次请求不新建投递、不上传或发送。gateway保留已完成任务和原摘要，将该输出标为失败并生成一次通知，不运行Agent重做或重写文件。

已存在相同key时，先核原定kind/name/摘要与原投递指纹，直接返回原回执，再按原taskId对账；生产者文件变更或删除都不能让一次已发送的任务变成“未发”或重新上传。摘要不同仍拒绝key复用。指纹格式不变，旧版创建的发送记录可匹配。

旧gateway未终态file/image队列只从原任务已持久化的artifacts摘要补字段，不读取当前文件来生成“原摘要”。缺少唯一有效原证据时保留未决/错误，不发送、不猜测、不自动标失败。终态历史行不迁移；真实账本本轮未处理。

本接口对其他CLI/HTTP调用者是可选增强：未提供摘要的普通发送仍采用原有“本次读取字节”语义，不声称绑定更早的任务版本。它不是防止同一OS用户恶意修改所有进程/数据库的沙箱。

## 验证与现场边界

11项新增专项覆盖排队后变化、file/image、旧任务升级、原证据缺失、未知回执重启、HTTP成功丢失、源文件删除、读取后变化、并发回执优先、参数拒绝，以及真实loopback HTTP/CLI/Gateway错误映射。HTTP进程运行的是合成CLI，不是真实DWS；原版DWS、Keychain和账号均未调用。

最终源码、Python3.14和Python3.11隔离新wheel各实际执行291项全量通过，六入口/21模块及随包MIT许可证匹配，12项冻结核验通过，见[结果](../../evidence/2026-11-12/artifact-digest-adoption-validation.json)。冻结源、测试及wheel在local/artifact-digest-final-20261112，首轮290项/3失败等原样保留，不用HEAD反推历史安装结论。未部署、未新增钉钉UI通过；E090恢复提案仍未授权，其E084产品摘要也不能当作本次版本的部署计划。
