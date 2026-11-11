# 需求回顾与当前真实进度

2026-11-12，E054之后。交付目标与MUST/SHOULD未变。当前是已接通本地Kimi的普通账号IM实验产品，能实际承接已授权会话中的任务与文件；**整个项目尚未验收完成**。唯一活动清单是[plans/completion](../plans/completion/INIT.md)，逐项判定以[验收矩阵](../plans/completion/ACCEPTANCE_MATRIX.md)为准，不用历史测试数量替代当前结果。

最新修复为[附件缓存清单完整性](71-download-cache-integrity.md)：6种损坏拒绝及显式repair通过，48现场缓存/55资源只读核验，双Python已安装包各180项和22审计通过；三进程空闲加载，无新消息。此前[异常消息隔离](70-malformed-message-isolation.md)：18形状隔离且后续合法任务继续，双Python各179项、302条旧官方事件投影相等及25审计通过；两gateway空闲加载，传输和原观察保持，无新UI。此前[并发对账终态保护](69-monotonic-reconciliation-and-ui.md)：旧线程8/旧安装HTTP4失败保留；修复后Python3.14与最低3.11隔离wheel各177项，三进程已加载。新的veil原生私聊由Kimi实际计算平方并回传145B JSON，liev完整回复、客户端下载及Quick Look打开通过，36审计7负向；原任务/会话/日志保持。此前[中文路径验证](68-unicode-workspace-install-validation.md)、[交接契约](67-current-handoff-contract.md)、[冻结历史审计](66-frozen-install-audit-boundary.md)与[真实超时](64-runtime-timeout-and-installed-wheel.md)各按当时版本保留，旧失败和未验格子不改绿。

## 当前交付状态

| 目标 | 已验证范围 | 仍缺/限制 |
|---|---|---|
| 通用工具与真实执行 | CLI/HTTP/consumer、多路由、队列/会话/outbox、至少一个Kimi真工具执行 | Codex超时单独跟踪；不是OS恶意隔离 |
| 身份与双向收发 | veil真人UI输入，liev真人DWS回复、AI发送标识；原两账号群/私聊基础路径 | 原群新增第三人后新实验暂挂；外部/bot无现场结论 |
| 附件与媒体 | PDF/DOCX/XLSX/ZIP四方向；私聊TXT/CSV、原生PNG/JPEG、WAV/MP4 file、下载打开和实际工具 | 群TXT入站/CSV双向等仍缺；语音条/独立video不由文件替代；详见四方向矩阵 |
| 长文、引用、组合 | UTF-16分段、完整长气泡UI、私聊出站引用、单条双PNG、分条多文件后续合并 | 私聊入站/群引用、其他单条多附件、群长文未过 |
| 控制与失败 | 私聊status/cancel/new、实际取消、拒绝对账、模型错误保留、超限提示及新压缩任务 | 群控制等仍缺；未知先对账、从不静默重做 |
| 运行与恢复 | manager、只读doctor、新venv六入口/19模块；E054 Python3.14/3.11隔离wheel各180项通过；manager私有诊断已补，历史关闭错误根因未解；短停机、history/Stream限定故障、自然access预刷新 | 真实失效refresh与完整24h未过；E027原during-shutdown诊断问题保留 |
| 官方办公 | 绑定liev的doc/todo/calendar/未发送draft、个人钉盘上传下载及合成语音听记真实任务与IM文件 | 独立会议、密送独立读证、外部场景按SHOULD保留 |
| 文档与Git | 官方/补充边界、研究引用、合成fixture、只读审计、manifest/隐私门、分段本地提交 | 最终自检、封版和完成标签未做；未远程发布 |

运行配置仍为两路精确liev profile，DM启用官方办公上下文、群关闭。E052快照DM62任务/154outbox（153确认1旧拒绝）/163传输/226事件；群3/7/12/76。manager控制传输和两gateway，历史ctl已退出。原观察起点11月11日19:36:08，07:37附近约12.020小时；累计6不可达、3poll_error和维护保留，最早11月12日19:36后评估24h，不能声称零中断。

## 用户从一开始要解决的问题

把钉钉变成本地 Agent 的群聊/私聊工作入口，承接任务、文件、多轮补充和结果交付；同时建立可复用方案和知识库，使后续项目能确定：哪些业务会话官方原生能力可以覆盖、哪些有明确限制、开通和开发怎么做、必要时 bridge 补哪里，以及如何验证整个系统持续有效。

用户既有 WeCom bridge 已采用 macOS AX；钉钉应先尽可能使用官方工具，不预设需要完整移植 AX。真正的普通账号路线是为保住实际业务覆盖，特别是跨组织、含外部成员和外部客户交流；用户明确说钉钉 bot 只是“可能”受限，要求调研确认。

## 对话要求追溯

| 用户提出的要求/调整 | 对项目的约束 |
|---|---|
| 深度调研文档、背景、知识、技术、项目 | 产物必须解释官方能力、身份模型、相关项目和限制，不只是保存 CLI Help |
| 私聊/群聊，双向文本、多媒体、文件 | 接收、发送、原件、原生呈现、主动投递分别验证；单群自发自读不是完整双向验收 |
| Agent 调用组织内文档、邮件、会议、待办等 | 建立办公能力/权限矩阵；文档、待办成功不等于全套办公完成；日程和在线会议分开 |
| 参考 GitHub/fyaic 的本地 WeCom bridge | 参考已有调度、幂等、媒体、恢复和 Agent 接口；不直接复制钉钉未验证的 AX 结构 |
| 尽可能使用钉钉官方原生工具，再实现 bridge | DWS/其他官方路线先核对；只有具体缺口成立才决定 AX；不能以旧版缺口否定新版 |
| projects 下沉淀所有调研、探索和经验 | 本地知识库要能供新项目/服务直接接入，包含证据、步骤、错误与解决方式 |
| 必要时本机实测，人工介入列清单 | Agent 完成可独立工作；人工只处理真实必要的权限、登录或业务选择 |
| 改用新组织，用户是管理员且手动开通 CLI 权限 | 当前范围为弗忧智能科技默认群；旧恒泰进结果不继承；管理员手动开通是本案例已确认前置 |
| 普通账号动机源于原生 bot 的潜在限制 | 必须对照 bot 与用户身份的会话覆盖；不照搬企微限制，也不假设 Slack/Telegram 完全无限制 |
| 目前单人群，涉及多人的先跳过 | 历史限制；最新授权已恢复veil与liev在原群及私聊测试，其他对象不自动扩大 |
| 本机 Codex 或 Kimi 真正接入，参考 WeCom/Slack/Telegram | 必须跑通任务执行、原生上下文、文件回传；不能将通用性解释为不接 runtime |
| 执行、验收、完善计划形成连续闭环 | 阶段汇报不作为停工理由；做完一项继续无依赖项；确有外部阻塞时准确记录 |
| 回顾所有消息，明确文档需求和真实进度 | 把知识库、实测、实现三类进度分开，不用文件数量/代码量代替业务完成度 |


## 证据与边界

官方DWS负责认证/profile、通讯/资源和办公；自研补普通账号的任务执行、幂等/恢复及明确缺失的本地image上传叶子。bot已有官方dev connect/OpenClaw/数字员工路线，不再把所有bot接入当自研缺口；没有创建bot。[官方边界](25-official-boundary-and-scenarios.md)、[通用接口](22-generic-tool-and-consumer.md)、[运行手册](15-service-runbook.md)。

API、资源原件、runtime真工具、原生UI、客户端下载打开分别计证；完整映射在[EVIDENCE](../plans/completion/EVIDENCE.md)。旧failed/blocked/cancelled/rejected及错误模型文字不会因后续成功被改绿。所有原始账号、聊天、AX/截图、令牌和下载件只在local。

曾经仅靠追加后记导致“未测/已过”“当前版本/历史版本”混杂；本页已改为当前表格，旧全文按字节保存在[历史总状态](history/through-E035/17-requirements-progress-review.md.txt)，原实验详情和推进账本继续保留。下一步只由[关键路径](../plans/completion/CRITICAL_PATH.md)和[任务池](../plans/completion/TODO.md)推进。
