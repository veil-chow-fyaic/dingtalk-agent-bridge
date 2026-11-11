# 官方凭据自然轮换观察

2026-11-12，E028。E028：59次readonly元数据采样观察到官方access到期时间由02:44:32延长至04:39:40，02:40:06首次观测，距旧到期265.918秒；轮换后双路完整history同步继续。19只读审计/3负向检查通过，采样期间部署造成1次本机health URLError原样保留，不算全程零故障。没有复制/改写令牌、撤销授权或改系统时间；不等于失效refresh凭据恢复。原24h观察冻结849样本7.07h/6不可用，起点/PID保持；DM40/97/106/147、群3/7/12/76均未新增。

本段是L4运行/元数据证据，不冒充新的客户端UI任务。前段双图和引用的真实UI证据分别在docs/45与46。

## 方法与观察

只读采样器每约30秒调用固定v1.0.67的`auth status --readonly --profile <route profile> --format json`，仅保留成功/有效期/授权状态字段，再读取本机HTTP health。它不执行普通auth status/login、不读取或复制token值、不修改任何授权/时钟。正常bridge请求仍按既有15秒补读和Stream配置运行。

59次采样中最后一次首次观察到access有效期延长；refresh仍有效。轮换发生在旧access到期前的官方5分钟窗口内。时间来源为机器实际时钟；记录的是首次观测，不精确指认是哪一条history请求触发刷新，也不把新expires_at减去假定TTL作为已知刷新时刻。官方负责刷新，bridge没有新增OAuth逻辑。

02:26:04采样读取本机health出现一次URLError，处于E027部署维护期间。该样本的官方readonly元数据仍保存；原24h观察也保留维护不可用计数。其余已取得的health样本未见poll_error，但这不能消除缺失的那次健康响应。

轮换后独立再读readonly状态，expiry保持新值、身份仍有效；两路last_sync均完整且时间晚于首次轮换观测，timer_cycles继续增长。原E027后jobs/outbox/deliveries/events/runtime日志逐行保持，没有新消息、重放或模型任务。原观察器PID归属另以ps命令核对为capture_service_observations.py及原run、86400秒/30秒参数。

## 复核和边界

只读`python3 scripts/accept_auth_rollover.py`，检查冻结采样与collector摘要、状态/窗口/同步、无新增账本和原观察器；[台账](../evidence/2026-11-12/auth-rollover-ledger.json)、[负向验证](../evidence/2026-11-12/auth-rollover-validation.json)。内存中把后续expiry改回旧值或注入路由poll_error均使验收失败；原始记录不改。

凭据和ID不入Git，原始采样/健康/快照仅在local/auth-rollover-20261112。本轮一次性采样任务完成后退出，原24小时观察器继续。不能据此声称撤销/过期refresh凭据后恢复、需要用户重新授权的流程、Stream重鉴权或24小时稳定性已通过。

固定官方源码已说明readonly与运行时刷新分工，见[官方边界](25-official-boundary-and-scenarios.md)；不复制第二套认证逻辑。

02:45:09跨旧expiry补验：原access标记02:44:32已过，再次readonly仍显示新expiry/有效身份，两路last_sync均在旧到期点之后完整成功，聚合/路由无poll_error；19项审计与3项负向检查最终通过。此检查仍不是失效refresh后恢复。
