# Pi 部署与真实私聊验收 E123

产品e7d82cc已部署。AIC测试群保留Kimi；原veil/liev私聊已显式迁移Pi 0.84.2，原Codex会话经真人UI的`/agent new`归档。三个服务运行，DWS ready，仍是liev真人账号向veil回复，没有新bot或权限变更。

| 真人客户端动作 | 实际执行和用户可见结果 |
|---|---|
| veil发送E123-Pi-1 | Pi实际bash/Python计算13×41=533，再用write工具写JSON；liev文本和14B文件可见。任务要求由同一个Python程序写文件，这个工具选择细节未遵从，不能宣称完全逐字遵令 |
| veil继续E123-Pi-2 | 同一原生Pi session；实际Python读取533、加9得到542并写26B TXT；liev旧值/新值和文件可见 |
| 两个文件下载 | 都从钉钉保存到本轮local目录；Finder Quick Look打开JSON及TXT显示正确内容，SHA与交付原件一致 |
| veil发长任务再cancel | 实际前台Python写起始时间，计划sleep90后写late；真人客户端显示“已请求停止当前任务”“任务已停止”；95秒后无late，捕获的3个自有子进程退出 |

94旧任务与原outbox保留，新增2完成工具任务、1取消工具任务、1完成取消控制任务；9回复confirmed且官方history均回读为liev自身消息。群任务和session没有改变。31项部署/UI/账本核验通过：[脱敏证据](../evidence/2026-11-13/pi-deployment-ui-validation.json)。E122同一冻结产品的396×3为对应离线证据；最终测试比早期版本增加了Codexfixture的ready后到期控制，产品没有因此改超时。

## 真实启动失败与恢复

首次完整启动在conversation-info处收到DWS api/request_timeout，exit1、stage=request、3872ms、providerExecutionStarted=false；尚未发送任何新UI任务，错误原件保留。无凭据TLS连接两个官方域名均成功，父环境8个网络变量都为空。按已有恢复授权仅做一次有界分阶段恢复：先transport补至新的固定cut，gateway停机核watermark和无history_window，排空/停transport、审查零积压后启动三个组件。成功不表示瞬时失败的根因已经找到；没有auth/login/doctor/Keychain调用，没有反复自动恢复。

固定官方源码将request_timeout映射自context.DeadlineExceeded。默认DialContext为3秒，这是约3.87秒故障的一个排查线索；该分类也可来自别的上下文期限，现有信封没有失败连接阶段，不能据耗时认定DNS/TCP/代理或服务端的唯一原因。未扩大DWS超时或改变网络配置。本次错误与原系统钥匙串事故分开跟踪。

## 适用范围和后续

Pi已完成文字任务、普通文件输出、同session续接及取消的本地和私聊UI闭环；图片输入明确未声明。不能外推所有模型、插件或OpenClaw。AIC Kimi与原Codex E120证据保持，不重发旧样本。

原独立24h观察aic-persistent-env-20261113仍为同一run，保留本次维护和首启失败；不能称同版本连续健康24h。系统最初根因、自然刷新、剩余原生语音/video、引用、多附件和7个MUST缺口保持。当前49/14/1不变，项目未完成。

下一段核OpenClaw官方入口与唯一turn宿主、Qwen接纳/完成和本地事务边界；DWS超时需新的阶段证据才能收敛，不重复认证或旧媒体探针。当前固定安装包已有E122验证；E121交接包仍是旧982ae49版本，后续更新交接须说明代码差异，不把旧包标成Pi版。原始UI、下载、配置、六库、进程和错误日志仅local/pi-adapter-20261113。
