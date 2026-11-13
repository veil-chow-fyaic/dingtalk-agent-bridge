# 上游报告草稿：Darwin超时未传播到keyring子进程

状态：本地草稿，2026-11-13。没有向官方或社区发布，未包含账号、凭据、原聊天或系统日志。

## 建议报告内容

**标题：Darwin keychain timeout leaves the underlying command running; preflight is outside the deadline**

固定范围：DWS v1.0.67，commit `63a7c4906c7dee10750011ea309b9eb78abb7eb0`；go-keyring v0.2.8。此报告讨论固定源码，不主张所有新版都受影响。

观察：DWS的waitDarwinKeychainWorker在deadline到期后返回Unavailable，但worker闭包里的keyring.Get/Set没有接收该context。依赖使用exec.Command，故等待者返回不能终止底层命令。另外checkDefaultKeychainAvailable在worker及计时范围外，预检查自身也可能卡住。依赖Set在Start之后才校验命令长度，部分早退分支没有Wait。

预期：预检查和真实读/写共享同一个预算；取消传到创建的命令并回收它，超时分类不被迟到成功覆盖；不配合退出应明确标为清理未完成。没有安全证据的读取错误不能作为新的自动写入/重试依据。不得杀掉与其他调用共享的进程。

复现不需要访问真实钥匙串：替换后端为阻塞的测试子进程，观察外层已超时而worker/进程仍存活。现有[E094复现源码](../evidence/2026-11-12/dws-keychain-timeout-probe_test.go)记录该缺口；新的[两层候选与复现工具](117-dws-cancellation-candidate.md)在固定源码上验证正常、失败、预检查、超时、回收和迟到结果。

候选结果：DWS10个方法、依赖5个方法分别在普通/race模式通过，均为选定源码和合成进程；未执行真实Keychain命令。补丁、SHA及许可随草稿保留。候选尚需依赖API设计、原测试签名迁移、完整CLI构建和平台测试，不作为现成发行补丁。

## 明确排除的结论

这项缺陷不证明macOS `SecKeychainLogin=-25293`或`exit status 51`的最初触发原因；也不证明取消一个命令能撤回系统授权UI。候选没有改变身份/存储策略，未解决原有无效DEK/并发`-U`/读回fallback语义，未处理Delete/DeleteAll。保留这些限制，避免将一个可复现的取消缺口扩大成“系统认证事故已解决”。

公开来源：[固定DWS Darwin实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/keychain/keychain_darwin.go)、[固定go-keyring Darwin实现](https://github.com/zalando/go-keyring/blob/v0.2.8/keyring_darwin.go)。DWS为Apache-2.0；go-keyring仓库LICENSE为MIT，而该Darwin文件保留Google的Apache-2.0头。两者原许可及文件声明分别保留，不能把仓库整体误称Apache-2.0；候选修改和新测试保留对应许可；不附带任何本机凭据材料。
