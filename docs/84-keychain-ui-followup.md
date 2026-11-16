# E067：用户输入系统密码后的只读核对

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12约09:48–09:58 CST。用户不知道“恢复钥匙串访问”的具体含义，随后报告输入过一次系统密码，并表示没有修改Mac登录密码或注意到拒绝相关提示。此前笼统让用户“解锁”不足以指导恢复，已明确纠正。

原生钥匙串访问已找到登录钥匙串的`dws-cli`条目，账户标签为`dek`。没有勾选显示密码；访问控制原本已为允许所有应用，保存更改按钮禁用，没有修改任何设置。菜单状态不能单独判断解锁，因此按本机Apple SDK `SecKeychain.h`定义，只读调用`SecKeychainOpen`/`SecKeychainGetStatus`，两个OSStatus均0，状态位7：已解锁、可读、可写。没有调用解锁、创建、删除或读取条目值的SDK函数。

用户输入系统密码后，官方固定版doctor仍auth fail，原两路history时间仍停在09:25。原任务/投递/会话/运行日志保持。Apple `security`对同一条目的单次读取诊断将stdout直接连接DEVNULL，未捕获、显示或保存密钥，返回51且stderr为空；不能从这个8位退出码臆断更细OSStatus或密钥损坏。官方Go keyring依赖会丢弃失败时CombinedOutput，本次没有额外错误正文可用。

下一步是普通系统终端与后台执行环境的一次对照，仍只运行固定官方doctor和原profile，不重新登录或迁移凭据。已准备私有脚本`local/sync-failure-20261112/terminal-doctor-check.py`，将原始结果留local、屏幕只显示检查摘要。电脑控制工具明确拒绝访问`com.apple.Terminal`，理由为安全限制；没有改用其他终端、Finder或脚本去绕过。已请用户亲自在终端运行以下命令，执行结果由助手读取，无需用户贴输出：

```bash
cd /Users/veil/Projects/dingtalk-agent-bridge && PYTHONPATH=. python3 local/sync-failure-20261112/terminal-doctor-check.py
```

对照结果到达前，不继续让用户盲目解锁、重复输密码或删除条目。若普通终端也失败，再据实决定官方恢复方案；当前尚无证据支持重置、迁移或升级。E066已证明所检查的macOS DEK源码在v1.0.68未变，并不是已验证的修复方案。

证据见[keychain-user-followup.json](../evidence/2026-11-12/keychain-user-followup.json)。密钥、用户密码均未保存；原始AX、系统状态、官方诊断和快照只在local。E065故障仍未恢复，没有新消息发送、服务重启、权限变更或新的UI验收通过。

## 10:07普通终端对照已到达

用户报告“已运行”，本机结果确认普通终端同样auth fail/default Keychain pass/network pass，不能将故障归因于Codex后台环境。后续不再重复请求终端诊断或输入密码。结果见[补充证据](../evidence/2026-11-12/keychain-terminal-followup.json)。

固定官方源码的`auth reset`会调用DeleteAllTokenData清整个auth-token命名空间和profile登记，并删除应用凭据等配置；这不是只修liev或只修DEK读取的操作。官方[恢复边界PR1430](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/pull/1430)也明确区分已确认密钥丢失/密文不匹配与未分类读取失败，后者保持拒绝，不能强行当成missing触发修复。因此未执行reset、删条目、迁移file-DEK或扩大权限。

系统层根因仍未知。可在用户保存工作后尝试重启Mac以排查钥匙串服务状态，但它不保证修复，会中断全部本机测试进程和原观察，必须由用户安排；不得自动重启或把重启前后算成连续24h。重启前已记录原配置/manager归属和所有证据，之后先核实际旧进程消失和原账本，再按原配置恢复；不能补发旧任务。
