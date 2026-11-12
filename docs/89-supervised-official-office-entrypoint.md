# E073 运行器官方办公工具统一受管入口

已消除生成上下文直接暴露原DWS binary的调用路径：schemaVersion 2的binary指向工作区0700私有入口，固定原路由profile、--as user和JSON输出，通过官方CLI完成业务。没有改原版DWS、复制凭据或调用私有协议。

受管入口复用E072的工作区暂停状态、两并发槽位及独立进程守护。支持当前已交付的doc、todo、calendar、mail、drive、minutes六类；命令族放在首参数。其余业务参数、原始stdout/stderr字节、退出码和当前工作目录保持。超时取已验证的runtime预算，默认600秒；听记现有180秒等待不被削为90秒。profile/as/format只能匹配固定值；auth、event、dev、mcp、账号配置及直接凭据覆盖参数不经该办公入口执行。

首次官方错误原始输出仍仅供任务私有日志使用；若匹配已观察的Keychain故障，会写入共享暂停。后续尝试在启动CLI之前返回固定脱敏错误。取消、超时、wrapper或gateway被SIGKILL时，由独立守护清理同组后代；保持“超时可能已创建对象、不得自动再创建”的既有办公契约。

这不是OS沙箱。runtime若故意绕过/修改生成入口，仍拥有本地进程权限；该限制不能被描述成任意不可信程序的安全隔离。已有运行器会话的旧上下文不算已迁移：下一次任务prepare才重写入口；现场服务目前停止且未部署，恢复时须明确核对。

9个新增测试方法，用真实合成进程验证：旧入口连续两次凭据读取的失败；六类参数/工作目录/二进制输出/退出码保真；14类身份/命令/凭据绕过拒绝；传输和办公双向共享暂停；无效超时启动前拒绝；timeout和wrapper SIGKILL后无晚写；实际LocalRuntime调用生成入口；gateway SIGKILL后跨两层守护清理。不是实际Kimi或DingTalk UI测试。

源码和Python3.14/3.11新隔离安装包各237项通过，六入口、21模块摘要匹配，14专项通过。[安装证据](../evidence/2026-11-12/official-proxy-install.json)、[冻结审计](../evidence/2026-11-12/official-proxy-validation.json)。原始证据仅local/official-proxy-20261112。保留首次6个路径断言失败（macOS /var 与 /private/var 同一目录，改按resolve比对）及全量1个旧gateway裸binary预期失败；没有把它们当真实平台故障。

本轮仅在项目local/runtime写入0600的operator_suspended标志，未调用官方CLI或读取钥匙串。这样受管bridge即使被误启动，也会先拒绝凭据调用。三服务继续停止，现场配置、官方binary、原24h观察均保留；没有认证恢复、消息发送、部署或新UI通过。

剩余Stream边界已核固定官方源码：[证据](../evidence/2026-11-12/official-bus-ownership-boundary.json)。bus的工作目录按DWS配置目录和身份共享，Setsid后独立存活；foreground分支只跑bus；stop先鉴权并删除订阅，剩余run state为空时才停bus，不能把单一subscribe_id无条件当成独占进程停止权。默认5分钟无消费者退出也不等于桥接退出即清理。没有执行status/stop，更没有使用--all。

下一段优先验证现有官方history收发模式的受控恢复方案：R03/R13要求收发与持久恢复，未强制使用共享bus；配置示例本就默认history。明确15秒补读、暂停Stream提示的当前能力边界，不擅杀共享进程或为恢复复制身份资料。该方案需要先完成离线验证和具体恢复步骤，再取得用户明确同意；在此之前保持真实DWS/auth/doctor/Keychain和后台启动禁用。
