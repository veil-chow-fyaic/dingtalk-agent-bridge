# 持久运行环境与DWS结构化错误诊断

2026-11-13，E115。沿用CEO C06“明确子进程环境”的接入思路，产品仍是runtime/组织无关的IM中间件。配置只影响Agent子进程及其工具，不改系统代理、HOME、CLI凭据或transport配置，不新增第三方依赖。

## 持久配置

`config.agent.example.json` 的 `runtime.environment` 默认 `{}`，保持既有父环境继承。确有网络需要时，在各自私有Agent配置中填入本机已验证的 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY`；支持全大写或全小写，不把测试机端口写成产品默认。空字符串/null显式移除对应大小写变量。冲突别名、控制字符、错误类型/代理URL及其他变量名在创建任务工作目录或启动子进程前拒绝。

配置值进入runtime guard，再由实际CLI继承。应用配置时同步大小写，NO_PROXY合并已有绕过列表并保留localhost/127.0.0.1/::1。父环境、HOME、认证资料不变；网络变量不改变runtime会话契约。离线 `dab-doctor` 仅检查合法性，不连接代理、不调用DWS、也不证明网络可达。网络依赖仍须在目标设备配置和实测，不能将此配置当作自动安装代理或开机自启。

配置重载应先等当前任务/回执终态，再按manager归属停止空闲gateway，修改私有配置并启动。若同时更新transport代码，则按固定cut补读、停机审查积压后恢复gateway。失败任务和未知投递不自动重做；记录始终保留。

## DWS诊断

受管聊天/资源调用及六族办公入口在原 `dws-call-audit.ndjson` 中新增 `result` 事件，与原attempt、PID、operation关联：

- phase：response/decode/process/spawn，区分提供方响应、解析、守护/进程、启动失败。
- outcome：response_ok/response_error/invalid_response/process_error；response_ok仅代表CLI响应，不等于IM已送达。
- exitCode、elapsedMs及明确的category/reason/server_error_code/origin/stage；类型和值均白名单，不认识的值记unclassified。
- providerExecutionStarted/providerRetryable只保留布尔值，automaticRetry恒false。未知发送仍按原key对账。

不写参数、消息/错误正文、URL、profile、账号、token、provider actions/details。诊断写失败不能把已成功的发送改成失败或吞掉回执。办公入口仍原样返回调用者所需的stdout/stderr/退出码，诊断日志另行收敛；原始运行记录仍只留local。凭据存储失败继续持久暂停，普通上游超时不自行推定为token过期，系统调用超时/中断沿用受管防护。

错误标识被用于运行状态时，只显示白名单代码或通用失败；不会把提供方任意文字串进健康信息。已知reason不能被未知server_error_code遮蔽。历史E112只有request_timeout的旧记录无法据此补出原始信封或唯一根因。

## 验证与边界

专项包含真实合成CLI读取重建runtime后的环境、父环境与身份变量不变、旧session/任务/回执保留、离线校验无副作用、各种错误信封/进程异常、办公原始输出一致以及日志写失败不丢回执。冻结源码和安装包验证结果见[证据](../evidence/2026-11-13/runtime-environment-diagnostics-validation.json)。

初轮专项发现未知server_error_code遮住request_timeout，修复后9项诊断专项通过。初轮全量已经加载修复前模块，保留2失败；首次冻结源码测试放在无产品包的安装测试目录，部分测试自己重置PYTHONPATH后产生15失败/2错误，属于测试布局错误。改在包含同一冻结产品与同字节测试的源码目录运行；原失败日志完整保留，不改断言、不当作产品已验证。安装测试继续在无源码包目录导入site-packages。

这两项关闭的是“重启丢失进程环境”和“业务错误丢失结构化事实”的缺口；系统Keychain最初故障根因、官方worker取消缺口、自然续期及长期可靠性仍按[风险表](114-dws-risks-and-resolution.md)开放。产品测试通过不能替代两路UI交办、真实工具执行、回复、客户端下载打开的验收。
