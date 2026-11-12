# E072 DWS受管调用停止重试与子进程清理

本段只完成桥接传输层的离线防护，真实DWS仍停机，未修复macOS认证，也未新增钉钉UI通过格。

已实现：
- 官方RPC与Stream连接准备最多两个并行，以文件锁跨线程/进程限制；不是按账号重新放开。已建立的订阅不占用这两个短调用位置。
- 精确已观察的Keychain错误、超时、执行所有者异常退出会持久暂停本工作区后续DWS调用，涵盖history、发送/对账/资源及图片补充。并发成功不能擦掉失败状态；已有在途调用可能完成。
- 启动前写持久占用标志；父进程崩溃后再次使用会阻止自动重启调用。暂停状态不含提供方原始错误、账号或凭据。
- 重用独立runtime守护，主进程退出、调用超时、父进程SIGKILL及主动停止时，清理其拥有的CLI进程组。通过父进程生命周期管道触发，不扫描或杀其他应用。
- health增加工作区dws_access；doctor对已暂停原因只构造固定脱敏说明。原unknown发送保持同key对账，不自动重发。

操作契约：`python -m dingtalk_bridge.dws_access status`只读本地状态。`resume --confirm-retry`仅是管理员显式允许未来调用，不会自行调用DWS或读取钥匙串；必须先停止调用者并处置原因。它不是修复钥匙串或清空凭据的命令。本机目前禁止执行恢复，等待下面两项防护缺口处理完毕及明确同意。

验证：旧实现实际合成CLI退出后遗留子进程的失败已复现。12个新增方法覆盖TERM不退出的后代、超时、父进程SIGKILL后3.1秒无晚写、主动停止、并发账号/图片补充、持久暂停和显式恢复、损坏状态、Stream握手/已连接状态与重连暂停、标准输入保持打开直到主动停止。原6项凭据测试调整为显式恢复；实际HTTP重叠对账和同key不重发仍通过。源码、3.14与3.11隔离安装包各228项通过，六入口及20模块摘要匹配。详见[安装证据](../evidence/2026-11-12/dws-containment-install.json)和[冻结核验](../evidence/2026-11-12/dws-containment-validation.json)。最终日志仅local/dws-containment-final-20261112；首版227项安装产物仍保留local/dws-containment-20261112。

保留失败：初版全局串行导致4个真实本地HTTP重叠对账用例失败，另1个mock仍指向旧subprocess入口；已改最多两个调用并修测试接缝。首次0.5秒合成Stream测试超时发生在子进程建档前，保留原错误，将测试预算改2秒并重新完整验证，不把缺文件当平台问题。复核又发现原Stream PIPE被通用包装改成DEVNULL，初版227测试未覆盖；新增真实stdin读取进程在旧安装包失败，恢复PIPE并最终228项验证。历史E068测试按冻结Git版本核验，篡改冻结测试负向拒绝、旧报告原字节保持。

尚未覆盖，阻止当前部署：
1. 官方[event bus启动实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/event/busctl/spawn_unix.go)用Setsid创建脱离父组的bus，不能声称本段守护覆盖它。官方[personal event命令](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/app/event_personal_command.go)的foreground分支直接运行bus，不是当前stdout消费协议；不能随手加参数当修复。下一段须明确独占bus归属、官方停止方式和无账号验证，或受控history模式的产品边界，不能杀共享bus。
2. officialDwsTools上下文目前仍把原官方binary交给runtime，直接调用尚未走上述暂停及清理。须补薄包装和真实合成runtime测试，保持官方参数/输出及身份边界。

进程组守护不覆盖恶意脱组、守护自身被SIGKILL或系统失效。当前测试全用合成程序，没有执行真实DWS、doctor、auth、Keychain、登录、解锁或UI发送。三服务停止，官方binary/现场配置不变。原观察继续保存停机与故障，不能写成24小时健康或完成验收。

后续E073已离线补齐生成办公入口的防护，见[docs/89](89-supervised-official-office-entrypoint.md)。共享bus边界仍未解决，真实服务保持停机；本页228项为E072冻结版本，不与E073的237项混为一次执行。
