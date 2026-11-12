# CEO Agent Service：源码深挖与具体采用方案

2026-11-12，E097。对象是社区项目[callzhang/ceo-agent-service](https://github.com/callzhang/ceo-agent-service)，不是泛指CEO Agent，也不是钉钉官方产品。本次固定`92e360ed1eb35f006afee738916cc9b735c1deb5`，31份源码/测试/文档/许可选摘保存在local，每份已核Git blob、字节数和SHA256，见[完整索引](ceo-deep-dive-index.json)。只读源码审查，没有安装其依赖、运行其服务/测试、导入账号或调用DWS。

E093实际采用的旧版`bd3de36b136abfd5e3dc571347358ea5b1be69c1`及[摘要校验记录](artifact-digest-adoption.md)保持原来源，不用新版冒充当时采用版本。本次将CEO提升为**任务/交付/执行器契约的优先参照**；Qwen仍是DWS通道组件参照，两者用途互补。

## 适合借鉴到什么程度

CEO是本地优先、DWS/Codex/SQLite支撑的业务自动回复服务，有管理者画像、业务任务、办公和审核流程，不是独立通用IM SDK。它另有可配置bot路径，不能把这些路径的能力混算到DWS真人账号。[固定README](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/README.md)

值得深入的依据是可检查的失败处理实现和相应负例，而不是仓库名称、star或宣传：有原生回执校验、冻结产物、会话归属/兼容性、运行器能力和故障分类。CI声明Python分片测试、前端和浏览器测试；本次未核最新CI运行结果，也未本地运行这些测试，不能称其全部通过或已证明生产成熟。[Quality工作流](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/.github/workflows/quality.yml)

MIT允许按许可条件采用；真正复制时保留原版权/许可及修改说明。整包需要Python≥3.12及较大的Web/模型/业务依赖，而本项目当前Python≥3.11、核心标准库为主，不引入整个应用以获得几个通用机制。[LICENSE](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/LICENSE)、[pyproject](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/pyproject.toml)

## 1. 文件交付：采用已有收益，继续借负例

`DingTalkFileHandler.dispatch`冻结批准后的文件/目标、用稳定action key交付，保存provider回执后才读回确认；`reconcile`核原目标/文件名/摘要和回执，避免未知结果被当成重新上传机会。确认还要求目标会话和真实出站消息ID。[源码15–77行](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/dingtalk_file_delivery.py#L15)

测试覆盖`test_changed_or_missing_file_is_not_sent`、`test_target_changed_after_audit_does_not_send`、`test_unconfirmed_file_send_only_reconciles_across_restart`、`test_file_upload_timeout_does_not_repeat_provider_dispatch`、`test_receipt_from_wrong_conversation_is_not_completion`。[上游负例](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_dingtalk_file_delivery.py)

**本项目已采用一部分，不能写成全部待开发。** E093已修复排队后文件变化仍发送，任务file/image绑定原定SHA；E095已部署，E095/E096已有真实交付。`agent_gateway.py`冻结产物，`core.py`保存task再查询、原key对账、核会话并保护终态。下一步只将上游负例逐一映射到现有测试，发现未覆盖语义才补，不重造第二个发件箱。

## 2. “已发送”必须有发送事实

`DingTalkSendEvidenceDriver`不把模型填写的messageId、delivery key或任意读操作当交付证据；它核host记录的provider写操作，并把候选动作与任务代次、父运行和提案版本关联。**其中对无法分类的第三方工具存在接受自述的分支，且带正文的动作可因存在任一provider receipt而满足审核；本项目逐个投递确认不能照搬这些宽松分支。**[证据驱动器](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/dingtalk_send_evidence.py#L56)

其问题记录很有参考价值：递归找messageId可能把引用的旧消息当新消息；任务/查询key或笼统finished也不代表送达。当前`verify_message_send_result`显式只从发送结果所属结构取标识，冲突归ambiguous；使用历史回读证据时还核完整窗口、唯一匹配、会话/发送者/正文摘要。[问题和修复说明](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/docs/dingtalk-delivery-verification.md)、[当前校验器3814行起](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/dws_client.py#L3814)

本项目已经要求官方sendStatus成功、准确conversation和非空出站ID，quote提取不进入referencedMessage；不能以CEO发现过问题就声称本项目同样存在。值得优先采用的是**负例集合及可追溯的交付契约**：引用旧ID、嵌套冲突ID、另一任务/代次回执、状态pending、工具文字里的成功/429，均不得被归为新发送成功。保持API确认与用户UI可见两个证据层；不自动把文本相似的历史记录升级为confirmed。[测试](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_dingtalk_send_evidence.py)、[验证测试](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_dingtalk_delivery_verification.py)

## 3. 会话占用：先识别已有保护，再决定是否引入租约

Consumer在创建运行之前以conversation取得持久锁；TaskAgent的共享session lease具有唯一owner、续租、丢失即失败和仅释放自身锁。它防止不同任务并行污染同一模型会话。[Consumer锁](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/consumer_agent.py#L726)、[lease实现](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/task_agent_session.py#L17)、[归属设计](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/docs/direct-agent-session-serialization.md)

本项目`consumer.py`已有非阻塞独占flock和scope绑定，gateway为一路一个worker，不能错报“没有并发归属防护”。租约是**以后跨进程/外部宿主共用会话时**的候选，当前无需替换有效的本机锁。若采用，scope必须包含账号/profile、会话、执行器；不能复制CEO全局业务常量。失租后不得提交结果，旧owner不能释放新owner，重启不能复活旧任务。[租约负例](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_task_agent_session.py)

## 4. 会话兼容性：比“有session ID就续接”更明确

CEO按route和conversation保存session，调用时要求合适的contract hash。测试检查developer契约/选定Skill改变时不错误复用；Skill指纹使用该轮冻结材料，而不是之后变化的文件。普通提示修改与协议不兼容并非一律同等处理。[会话选择](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/consumer_agent.py#L681)、[fingerprint测试](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_consumer_session_prompt_fingerprint.py)、[Skill契约测试](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_consumer_skill_session_contract.py)

本项目绑定当前是scope/runtime kind/binary，已有schema2办公上下文升级及原session保持；还没有独立的adapter契约版本/能力指纹。这是S2可落地的明确设计接缝：增加可解释的兼容性元数据，区分正常提示更新、工具协议变化、runtime更换。**不直接照搬自动清空session**；不兼容应明确停止或按用户明确的新会话动作处理，旧历史和失败保持。

## 5. Runtime契约：适合支撑Codex、Kimi、Pi、OpenClaw

CEO把route、凭据模式、事件类型、错误类别、是否可重试/可切route/需暂停分开；静态能力清单与带健康状态/检查时间/有效期的动态快照也分开。源码支持的运行器不是本项目的四者，这里采用的是设计。[Runtime契约](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/agent_runtime_contracts.py)

建议本项目用独立、无DWS字段的轻量协议，而非引入整个Pydantic/业务依赖：

| 契约面 | 必须表达 | 对本项目的意义 |
|---|---|---|
| 调用 | start/resume/cancel，workspace，inputs，有限deadline | CLI和原生协议均能适配，不把Codex字段塞入通道 |
| 输出 | session、progress、明确terminal success/error、文本和有摘要的产物 | 退出码0或普通日志不能代替完成；最终发送仍由host掌控 |
| 能力 | text/image/file、tool execution、resume/cancel等静态声明和实际证据 | 声明能力不等于当前账号/安装健康；不支持就明确拒绝 |
| 错误 | auth/transport/capacity/capability/session/result/process/unknown | 能解释和选择恢复策略，不把每个非零退出都当登录坏了 |
| 执行归属 | standalone gateway或宿主原生channel二选一 | OpenClaw持有Agent turn时中间件只交消息，不再启动本地Kimi重复执行 |

未来共享一组adapter契约测试：续接正确会话、能力不足拒绝、部分stdout/坏JSON/非终态退出、取消无晚产物、产物路径/摘要、恢复不串任务。Kimi现有闭环作基线，Codex先闭环，再Pi/OpenClaw。不能照搬CEO某些自动切route策略：发送主体不切账号，执行器切换不能自动重放有未知副作用的任务。

## 6. Codex超时：借诊断方法，不能认定同一病因

CEO的adapter显式构建子进程环境、区分provider结构化错误和工具输出，并有“工具输出429不能判成provider容量问题”“终态成功不触发失败动作”等测试。固定新版还保留服务启动配置的代理环境；可作为本项目终端与服务环境差异的排查线索。[Codex adapter](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/codex_runtime_adapter.py#L180)、[对应测试](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/tests/test_codex_runtime_adapter.py)

本项目现有LocalRuntime继承父环境，并非已采用CEO白名单。因此不能直接归因“我们丢了代理”；`--ignore-user-config`、实际命令版本/参数、事件终态和服务环境都需对现有私有失败日志核证。只记录必要配置是否存在及脱敏差异，不读取/复制凭据，不通过静默改HOME、重登录或放大超时冒充修好。

## 7. 明确不抄的部分

- 管理者人格、OA/OKR、固定组织策略、全局TaskAgent业务scope、强制A/B审核和跨业务自循环，不是通用IM中间件要求。审核可留host扩展点，不能强迫每个聊天任务走该业务流程。
- `run_external`默认可捕获任意异常并自动重试；不能套在DWS发送或认证上。未知投递必须原key核实，自动认证恢复不符合本项目已确定的事故边界。[重试实现](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/external_retry.py#L84)
- `bounded_process.py`杀leader并无界join读管道线程。根据源码，后代继承管道时存在清理阻塞风险；这是静态推断，本次未执行复现。不能替换本项目已验进程组/父死亡守护及有界清理。另一个`process_runner.py`区分有效stdout进展与stderr/半行，并清理进程组，可借“语义进展”概念，仍需本项目合成后代测试。[bounded_process](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/bounded_process.py#L18)、[process_runner](https://github.com/callzhang/ceo-agent-service/blob/92e360ed1eb35f006afee738916cc9b735c1deb5/app/process_runner.py#L25)
- 历史数据修复/表迁移文件是CEO专有账本操作，不直接套到本项目；下载到参考目录不表示已选为产品组件。本次`action_delivery_storage.py`仅作迁移边界检查，不把它误报成通用outbox实现。

## 可执行的采用顺序

| ID | 状态/顺序 | 接缝与工作 | 验收，不以阅读源码替代 |
|---|---|---|---|
| C01 | 已采用并部署 E093/E095 | 文件原定摘要门槛；保留旧固定版与MIT | 已有11新增专项、三环境291历史验证及最近UI，不重跑旧样本 |
| C02 | E102已落实窄修复/待部署 | `core.py`/gateway发件箱；发送事实负例逐项映射 | 假/引用/冲突/跨任务回执不得confirmed，未知不重发；已有等价用例则记映射，不重写 |
| C03 | E099结果分类已部署，能力/终态继续 | `agent_runtime.py`薄适配器、类型化终态/能力/失败 | Kimi旧行为保持，Codex合成事件失败分类可解释，协议不绑定DWS；再真实第二runtime闭环 |
| C04 | 随C03小步实现 | gateway会话兼容性版本、冻结任务契约 | 合法续接/升级保持；不兼容不静默抹session；历史/回执原样 |
| C05 | 有多宿主需求再做 | consumer归属/租约 | 两实例不能同时用同session；失租拒绝提交；不得降低现有flock防护 |
| C06 | Codex独立排查线索 | 子进程环境、进度/终态和错误分类 | 可复现原超时或解释具体失败，正常任务UI闭环后才声明支持 |

每次仅导入一个有必要的接缝；固定来源、许可、修改范围、合成负例、安装验证和实际UI分别登记。**本轮交付是可复核的31文件研究与采用计划，不是31文件已移植、上游测试通过或新增Agent支持。**

E102已将C02负例落实到本项目，旧8方法22子场景失败，冻结修复三环境各307通过；只改core，未知不重发，不引入业务审核/相似历史确认。[具体对照与部署边界](../106-send-evidence-contract.md)。
