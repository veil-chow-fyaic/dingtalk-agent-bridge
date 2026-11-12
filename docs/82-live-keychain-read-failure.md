# E065：真实DWS登录密钥读取失败，尚未恢复

2026-11-12约09:25 CST，现有两路history同步开始报告BridgeError。群最后成功同步为09:25:18、私聊09:25:19；Stream监听仍显示ready，不能据此判定消息同步正常。本轮没有新UI发送、授权操作、凭据改写、服务重启或网络故障注入。

固定官方DWS v1.0.67的一次只读history返回退出51：`resolve access token: load access token: load from keychain: read DEK from macOS Keychain: exit status 51`。随后一次官方doctor进程退出0，但检查结果为auth fail、keychain pass、network pass、runtime_context pass、version warn。官方明确描述为“无法读取 macOS Keychain 中的登录密钥，无法判断登录状态”；默认钥匙串可用不等于能读DWS保存的密钥。不能将doctor退出0当健康，也不能将本错误当作已证实的refresh token过期。

源码定位到官方只读DEK查找遇到非NotFound错误即返回不可用，现有证据不能区分锁定、条目访问控制或其他系统原因。原生系统窗口快照没有可见的Keychain授权提示。没有打开或提取密钥、禁用Keychain、复制凭据、重新登录、撤授权或改系统时钟。已请用户在macOS恢复现有DWS密钥访问，之后需验证原进程能否自动恢复；不会为掩盖故障而重启。

原观察`reliability-20261111`和PID97881保持；09:39附近冻结1685样本、14.047小时、7不可达、30个poll_error样本，完整性检查通过但零错误和24h完成均为false。后续故障采样继续累计，30不是固定最终值。不从统计中扣除本次错误。两路任务/投递/旧运行日志和既有会话保持，无未知新投递。

官方doctor还提示最新版本v1.0.68；仅版本提示已经观察，尚未核实新版发布内容或完成升级。当前继续固定v1.0.67，不能据此声称新版本解决密钥问题或已有等价图片入口。

脱敏事实见[证据](../evidence/2026-11-12/live-keychain-failure.json)。原始官方输出、doctor、快照和观察报告只存`local/sync-failure-20261112`。同路径已有history与doctor两份新证据，现在停止重复调用；等待用户处理或原观察显示状态变化，再做一次只读确认。

恢复后的顺序：核现有profile与原两路成功history时间推进、确认旧账本不重放、保存官方/bridge原始错误和恢复证据，再补原3人群TXT/CSV/原生图片/音视频文件及控制任务UI。用户已明确授权原3人群继续测试，两账号执行白名单不扩大。普通群文件当前不自动触发或下载给Agent；必须另验证明确群任务如何关联附件，不能人工把文件放进工作区再宣称自动闭环。
