# 钉钉 bridge 接手说明

**E136接手更新（2026-11-16）：** 已按本入口推进截止采集工具，见[范围与验证](../../docs/136-observation-cutoff.md)。新增schema v2截止账本/逐路事务时间/磁盘及配置摘要/manager维护/最终seal，30项观察专项在冻结源码Python3.14与3.11分别通过。23产品模块保持2467fe2/E134字节；本轮未部署、启动观察、复查业务或调度。加载版本证据仍缺，下一项见[TODO](TODO.md)，R13未完成。以下E135内容保留为交接时点记录，原“未实现”按当时解释，不能覆盖本更新。

2026-11-16，E135。用户要求整体检查后交接，本会话停止新增实现、实验和自动推进。项目未完成；这是工作交接，不是R01/R12/R14最终产品验收。先读本文，再读[AGENTS](../../AGENTS.md)、[当前任务](CURRENT_MISSION.md)、[关键路径](CRITICAL_PATH.md)、[TODO](TODO.md)及同一[PRD](01-PRD.md)/[矩阵](ACCEPTANCE_MATRIX.md)/[最终自检](10-自检清单.md)。

## 接手时最重要的事实

- 唯一工程：`/Users/veil/Projects/dingtalk-agent-bridge`；分支`codex/complete-bridge`。聊天目录不是工程。单Agent，不派生、不重写、不远程发布。
- 检查起点HEAD：`9bf2bf3bae8cb2fa91c804fbaf2c90051ac0b5b7`，当时工作树干净。本轮只提交交接/文档/脱敏检查记录；接手时用`git log -1`取得交接提交，不能把它写成部署产品。
- 实际部署产品：`2467fe2`，部署/通道证据E134；当前23个产品模块摘要与E133冻结测试和E134部署记录一致。本机manager从此源码目录启动，E133独立wheel安装测试另计。
- 最近真实客户端UI：E131。E134有真实API/history/官方原件下载，但没有客户端呈现/保存证据。当前64格为51通过/11阻塞/2部分；14 MUST为7通过/4部分/3未完成，不是项目完成百分比。
- 产品主线是通用钉钉IM channel，CLI/HTTP/consumer可以独立工作；gateway是可选执行器层。Kimi访问失败不阻塞通道主线。原R09只要求至少一个执行器，已满足，不追加四runtime全过门槛。
- `bridge`心跳实际为**PAUSED**，配置更新时间2026-11-16 09:42:42（北京时间）。此次只读检查发现，未更改或恢复调度。旧入口写ACTIVE不准确，现已纠正。正常业务服务并未随心跳停止；本轮也未停止它们。

## 此次实查结果和限制

2026-11-16 14:10:38（北京时间）进行一次只读交接检查，详见[脱敏记录](../../evidence/2026-11-16/handoff-review.json)。没有发消息、调用DWS/模型/UI、启动观察、重启服务、改绑定或重跑全量产品测试。

| 检查对象 | 结果 | 证据边界 |
|---|---|---|
| manager拥有的transport、agent-1、agent-2 | 三者running，归属匹配 | 本地进程存活，不等于上游/模型实时健康 |
| DWS持久准入 | ready | 只读已有guard，不是新认证探针 |
| 群任务/Agent outbox | 20 / 47 | 全表含meta/session与E134保存结果一致 |
| 私聊任务/Agent outbox | 79 / 193 | 全表含meta/session与E134保存结果一致 |
| 未终结任务、待确认Agent outbox、未知传输投递 | 两路均0 | 独立SQLite只读事务捕获时点；不是未来保证或六库原子快照 |
| 本地同步记录 | 两路complete、无history_window | 不用last_sync.at冒充固定cut覆盖，更不是自然refresh证据 |
| 产品/配置 | 23模块及配置摘要与E134相同；产品AST可解析 | 不声称运行进程内存已逐模块检查 |
| 文档/清单（交接编辑前） | 168份Markdown一致性、739项manifest通过 | 文档检查器不验证每条陈述与现场一致；此次仍发现心跳描述漂移 |

## 已完成到哪里

| 提交/证据 | 实际交付 | 不能外推 |
|---|---|---|
| `baf0995` / E130 | 群引用双向，history/consumer保目标ID/原文，原生UI可见 | 私聊入站引用仍未过 |
| `3a0e3ad` / E131 | 原生群一条文字＋双PNG入站、原件/顺序/暂存一致；失败反馈可见 | Kimi403，任务failed/runtime_terminal_missing，无工具/结果，不是模型成功 |
| `4fbedbd` / E132 | 整理现行资料、历史范围、索引及文档检查 | 文档量不是产品进度，自动化状态后来被本轮实查纠正 |
| `2467fe2` / E133 | composition新产品能力；字面文字＋1–9有序PNG/JPEG、逐项SHA、≤2MiB、全部验证后暂存、单一官方Markdown发送、持久幂等 | gateway未自动切组合交付；不是普通文件附件数组/原生媒体新协议 |
| `9bf2bf3` / E134 | 部署上述产品；群/私聊各一条文字＋双PNG confirmed，四张官方下载原件与源/暂存字节/SHA一致 | 无客户端呈现/逐图保存，无新模型任务；原99任务/240 Agent outbox/session保持 |

E133最后冻结源码Python3.14.6、同一wheel安装Python3.14.6及3.11.15各448方法通过，新增15方法；23模块/许可一致。E134另有34项只读证据检查及5个篡改负例，不计为新增产品测试或“453项”。此次只核原记录和源码摘要，不重跑这些旧测试。

E134两条自身媒体在gateway inbox按设计保持pending_media、attempts=0，无error；离线materialize已经核图序及字节，但未改变受管inbox状态。不能称其已normalized/ready，也不应为了清理状态而重放消息。

运行器：群仍Kimi；原私聊已经native new归档Codex、显式迁移Pi0.84.2。OpenClaw适配代码已随2467fe2部署，但没有配置绑定、真实provider任务或UI验收；Pi/OpenClaw均未声明image_files。保持既有成功与失败的各自范围。

## 检查发现的执行问题

1. 曾把Kimi403扩成整条IM主线的阻塞，后来又把UI不可读当组合API部署前置；这两次范围扩大都不成立。E133/E134虽已纠正，后续不能再把“某格受阻”写成“没有任何事能做”。
2. 入口反复同步部署/测试数字，却没核当前心跳，导致PAUSED仍写ACTIVE。文档一致性工具通过不保证外部状态准确。此次修正现行说明，历史记录不改。
3. **R13仍有可独立实现的缺口。** 静态检查`capture_service_observations.py`：到期只写active=false和stop_reason，未自动保存截止账本或固定加载版本证据。`review_service_observations.py`可读已有ledger.json但不生成它；`reconcile_observation_snapshot.py`明确事后快照不能证明历史截止。仅等待自然refresh没有解决采集能力缺口。
4. 不应把所有交付准备推迟到全部MUST已过。R01/R12/R14的最终签署需要整体条件满足，但清单、版本固定、无凭据安装/回滚预检的缺陷可以先修；既有已通过部分不为凑进度重复执行。
5. 旧实验工具并非都可重复调用。`local/composition-api-20261116/deploy.py`会真实停启服务，`channel_case.py send`会发真实消息；文件存在也不是重跑许可。接手应读代码和证据，不能执行整个目录。

## 建议接手顺序：先解决能独立推进的项

| 顺序 | 具体下一步 | 通过条件/停止边界 |
|---|---|---|
| 1，独立代码工作 | 完善R13新观察的截止采集：固定run开始/结束、部署版本/配置摘要、每路SQLite一致性截止账本及维护记录，接到既有collector/reviewer | 截止时间与snapshot开始/结束、watermark/history_window可核；采集失败/过晚/版本改变必须明确失败或限制。合成测试验证缺失、篡改、并发写、异常退出及迟到快照不会假通过。不自动停业务伪造共同原子快照，不读凭据；本轮未实现该方案 |
| 2，准备后才进行新观察 | 确定稳定版本、维护规则与真实截止采集后，使用新run-id进行所需长期观察 | 旧两run原样封存，新观察不抵消旧失败。24h完整、零记录错误、自然失效refresh分别计证，不能只看计时器；交接本身不启动观察 |
| 3，条件恢复后补客户端 | 新的UI可读证据出现后，查看E134既有两条组合消息，核完整图文、发送者、AI标识，逐图保存/打开/SHA | 不重发来补截图；当前同一路径两轮failedToCreateImageDestination后停止，不能改权限/重启Mac/换底层工具绕限制 |
| 4，缺协议/入口的格 | 私聊入站引用、普通多文件单消息、原生voice/video逐项找有证据的新入口 | 固定官方来源或明确原生控件/事件；受阻旧右键/菜单/快捷键、旧file播放、E056重复参数计划不重跑，不虚构类型 |
| 5，模型可选线 | 群Kimi服务访问恢复有新证据后才做新的模型验收 | 403仅说明订阅服务访问拒绝，不能断言周限额；不重发E131、登录修复、复制token或换runtime绕过；不拖住前四项 |

七MUST缺口仍为R01/R04/R06/R07/R12/R13/R14；最终完成只能按原判据。矩阵出站组合仍blocked指客户端闭环未完成，不能据其旧“尚缺”字样否认E134已成立的API/原件能力。原PRD/矩阵里的历史“当前”不应作为今天部署事实，现状以本交接及总览为准。

## 代码与验证入口

| 层 | 主要文件 | 定位 |
|---|---|---|
| CLI、HTTP、契约 | `dingtalk_bridge/cli.py`、`__main__.py`、`api/openapi.json` | 127.0.0.1:18768，显式account/conversation，send与原key对账 |
| 传输与原件 | `core.py`、`composition.py`、`routing.py` | 持久delivery、history、官方资源下载、逐原件摘要/顺序/幂等 |
| 持久消费 | `message_model.py`、`consumer.py`、`consume.py` | 保守投影、资源物化、自身过滤、隔离未知结构 |
| 可选Agent | `agent_gateway.py`、`agent_runtime.py`、`openclaw_runtime.py`、`runtime_guard.py` | 任务/session/outbox、终态、取消与进程边界 |
| 受管运行 | `service_manager.py`、`dws_access.py`、`official_proxy.py` | 实际归属、两并发、90秒请求＋最多15秒清理、故障持久暂停 |
| R13现有工具 | `scripts/capture_service_observations.py`、`review_service_observations.py`、`reconcile_observation_snapshot.py` | 先补截止采集缺口，不重审旧run |
| 新组合测试 | `tests/test_composition.py`、`tests/test_composition_http.py` | 14核心＋1实际回环HTTP/CLI，合成DWS，不是账号实测 |
| E134证据审计 | `scripts/accept_composition_api.py` | 只读已保存私有证据；不发送、不改inbox，不替代独立现场检查 |
| 交付门 | `scripts/review_documentation.py`、`review_acceptance.py`、`verify_handoff.py`、`verify_privacy.py` | 覆盖不足是正确失败，不通过改计数完成项目 |

以上省略目录的产品文件均位于`dingtalk_bridge/`。`pyproject.toml`为0.1.0、Python≥3.11、运行时标准库；六入口为dab/dab-bridge/dab-agent/dab-consume/dab-doctor/dab-service。macOS arm64已实机，其他平台未实机认证；工具包装/进程组不是OS沙箱。

## 本机证据定位与不可重跑项

| 路径（相对工程） | 用途 |
|---|---|
| `local/composition-api-20261116/` | E134部署、初次计划器拒绝、持锁审查、cut、启动、两路意图/回执/history/官方原件、前后六库；`group-send-result.json`及`direct-send-result.json`保存待补UI的原message ID，只在本机读取 |
| `local/outbox/composition-api-20261116/` | 四张E134原PNG；不替换或重新发送 |
| `local/next-channel-20261116/validation/` | E133冻结源码、wheel/双安装、测试日志及安装报告；Kimi单次复查材料在其上级目录 |
| `local/group-quote-20261115/`、`local/group-multi-image-20261115/` | E130/E131原始UI及入站/失败证据，不重放 |
| `local/handoff-20261116/review.json` | 本轮只读状态捕获，无新的业务实验 |
| `local/service-config.json`、`local/agent-config.json`、`local/agent-direct-config.json` | 当前私有路由、群Kimi、私聊Pi配置；只在本机使用，不输出值、不复制到新环境 |

旧reliability-20261111、aic-persistent-env-20261113已结束，不能重置/重审/追加数据冒充截止。E121的982ae49/683manifest是旧交接包，不能当当前产品。E125–E128 OpenClaw合成宿主/生命周期、E129官方diff、E115/E116环境修复、已过媒体/UI控制不重复凑数量。E133原生Kimi一次最小请求仍403、无周限额/重置时间；不再次探测。

E134普通部署计划器遇WAL/SHM拒绝，随后用了私有独立审查，并非通用脚本已支持所有旁文件情形。下次维护必须重新按当前状态评估；不能删除旁文件、改数据库、直接重放本轮local脚本，或把当时的0字节WAL当今日事实。

## 授权和交接后的动作边界

只准AIC测试群和原veil/liev私聊，多人实测暂跳过；禁止企业大群/旧群，不加人/bot/权限。liev是DWS显式profile真人、veil是原生客户端真人，测试身份不能固化为产品组织。原始身份、原聊天、日志、截图、数据库、下载仅local，不进Git或交接压缩包。

禁止真实auth/login/doctor、Keychain读取/锁/解锁、认证修复、file-DEK/reset/删凭据/复制token、改权限/重启Mac/绕系统工具限制；不索取密码/第二账号。正常受管业务不等于认证修复授权。凭据故障保持暂停，无自动恢复；未知投递仅原key对账，不补发。共享Setsid bus不杀，不用foreground冒充消费者。

必要维护依旧：先停gateway，transport按同一SQLite快照watermark≥固定cut且无history_window证明覆盖，再封新调用/排空/停传输审积压，才恢复执行；last_sync.at不是覆盖。更换runtime必须native new归档、零未决、显式binding迁移，不改配置硬绕，不将旧session交给新CLI。

用户已要求交接，本会话不再自行续作；心跳已PAUSED，不自动恢复，也不新建线程。下一位在用户明确接手后，先看上述独立R13采集缺口，避免再只读状态、重抄文档或等待Kimi。

可直接给接手者的指令：

> 接手 `/Users/veil/Projects/dingtalk-agent-bridge`。先读 `plans/completion/HANDOFF.md` 和 `AGENTS.md`，沿 `codex/complete-bridge` 单Agent继续，同一PRD/矩阵/最终自检，不重建或远程发布。主线是通用IM channel，Kimi不构成统一前置依赖。优先评估并实现新观察的截止账本/版本采集缺口，合成验证后再决定新的实际观察；不得重置旧run、循环旧UI或重发E134。部署产品2467fe2，最近客户端UI E131，心跳PAUSED；不自动恢复调度。所有已证、未证和禁止项以交接文件为准。
