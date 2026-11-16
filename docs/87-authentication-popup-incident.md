# E071 认证弹窗事故与停机边界

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


用户已确认弹窗停止，项目仍未恢复真实DWS收发。此次处理错误是未先停后台轮询就尝试系统钥匙串锁定/解锁；即使命令退出0，也没有证明登录可读或桌面恢复。向用户反复索取密码不能解决这一问题。

清理证据：三个managed服务停止；11个孤立DWS凭据读取进程、1个项目DWS进程，以及随后发现的2个孤立GitHub凭据读取进程被终止。最终DWS、凭据读取与解锁命令计数均0，但直到用户确认前仍保留桌面未恢复的事实。未给SecurityAgent发信号，未修改ACL、删除凭据、reset、复制token或重启系统。私有原始证据为local/reauth-20261112。

官方登录在OAuth之前拒绝覆盖无法读取的旧登录槽位。依据[官方参考](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/docs/reference.md)及[PR1430](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/pull/1430)，这是保护旧登录的失败关闭行为。macOS故障根因尚未确定；[Apple开发者论坛822120](https://developer.apple.com/forums/thread/822120)仅是相似症状和开发者 workaround 报告，不能称Apple确认本机根因。

独立空目录file-DEK探针只到授权URL即停止，没有登录。用户明确拒绝该模式，未启用准备的wrapper，继续保留系统钥匙串模式。

当前禁止真实DWS、doctor、auth、Keychain读取/锁定/解锁及服务自动恢复。原24h样本和维护中断保留。下一步E072只用合成程序复现并修复重复调用、直接子进程退出后遗留后代的问题。完成防护并说明恢复方式后，取得明确同意才恢复背景收发。此限制是本次事故后的执行决定，不是缺第二账号或群测试授权。
