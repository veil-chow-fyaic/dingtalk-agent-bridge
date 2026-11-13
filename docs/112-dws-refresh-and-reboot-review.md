# DWS续期、版本混用与重启后的状态

2026-11-13，E111。用户已自行重启Mac、Codex并重新登录DWS，询问是否每天授权过期或自动续期失败。本轮只读公开仓库、固定源码、二进制构建信息和本地服务账本；没有执行DWS/auth/doctor/Keychain，也没有改全局CLI。

## 判断

**每天重新登录不是DWS的设计要求。历史上确有刷新缺陷，但本机已有故障不能全部归为授权过期。** 官方[认证参考](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/main/skills/mono/references/global-reference.md)说明access token约2小时、refresh token约30天，正常使用时自动续期。固定v1.0.67的[token.go](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/auth/token.go#L247)在到期前5分钟判为需刷新；[OAuth实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/63a7c4906c7dee10750011ea309b9eb78abb7eb0/internal/auth/oauth_provider.go#L901)有进程内及跨进程双重锁、加锁后重读与凭据槽回写。只有完整OAuth登录态才具备续期条件，单独access token不能等同正常扫码登录。

E028已实际观察过一次自然预刷新：原到期02:44:32变为04:39:40，约提前266秒，随后跨旧到期点两路同步。此旧证据保留，既不能说从未刷新成功，也不能外推本次重新登录后的长期健康。原件与摘要见[自然轮换台账](../evidence/2026-11-12/auth-rollover-ledger.json)。

## 官方仓库已有反馈

| 来源 | 已确认内容 | 与本机的关系 |
|---|---|---|
| [DWS #1132](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1132)及[维护者回复](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1132#issuecomment-5762379764) | 多凭据槽refresh token不同步，刷新后旧槽失效；维护者明确v1.0.62修复，包含组织及legacy全局槽处理 | 桥接固定v1.0.67已有修复；终端旧v1.0.61早于完整修复，不能把两者当同一环境 |
| [DWS #476](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/476)及[维护者回复](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/476#issuecomment-5762849801) | 后台约2小时失效报告；维护者说明完整OAuth/Device Flow支持长跑，access-only凭据不足 | 报告使用file-DEK，和本机系统钥匙串路径不同，不能直接照搬解决方式 |
| [DWS #436](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/436#issuecomment-5761406189) | 老版macOS偶发权限错误、重登恢复；维护者表示已修复 | 没有精确修复版本，不据此判断所有重登恢复都是同一问题 |
| [Codex #60687](https://github.com/openai/codex/issues/60687) | macOS密码解锁后钥匙串失败，出现-25293及exit51，报告关联Computer Use Guardian；目前仍open | 本机E094系统日志高度吻合；社区评论的确定归责不是维护者结论，尚不能确认最终根因或修复版本 |

截至本轮，[最新release v1.0.68](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.68)已核。[v1.0.67到v1.0.68比较](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/compare/v1.0.67...v1.0.68)返回218个文件、53提交；其中没有internal/auth改动，也没有Darwin钥匙串文件改动，存在公共keychain及Windows隔离修改。不能承诺升到v1.0.68即可修复本机故障，本轮未升级。

## 一个实际的版本差异

只读取文件SHA和嵌入的Go构建revision，没有执行二进制：

- 普通终端PATH的dws为既有v1.0.61，revision `50eb73a0906c5911c5c25f9c7106b6ead4f14f62`；与最初[版本记录](07-local-results.md)一致。
- bridge固定使用项目内v1.0.67，revision `63a7c4906c7dee10750011ea309b9eb78abb7eb0`。
- v1.0.61源码已有双锁及组织镜像fallback，但尚无v1.0.67的legacy全局fallback。因此不能夸成旧版完全没有刷新保护，也不能忽略旧入口缺少后续修复。

用户在新终端登录成功只证明那次登录成功，不能代替bridge显式profile业务验证。后续应统一受控入口/版本，避免旧新CLI交替维护同一登录态；尚未证明版本混用造成了已记录事故，不擅自替换用户全局程序。主线继续固定v1.0.67和原profile，不复制token、不切file-DEK。

## 本机几次故障的区别

1. E071/E094：系统登录钥匙串解锁失败，DWS读取DEK报exit51，发生在业务API之前；不是token到期的证据。官方拒绝覆盖不明状态旧凭据属于保护行为，见[PR #1430](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/pull/1430)。我们当时后台隔离不及时、又安排锁定/解锁，放大了弹窗；这是处置错误，不能归咎用户。
2. E107：无主active调用槽触发bridge保守暂停；旧格式缺PID/阶段，最初中断来源未知，没有认证失败证据。E108已补归属日志，E109恢复并部署防护。
3. E110：钉钉和Finder同时failedToCreateImageDestination，是UI读取路径阻塞；当时DWS两路仍同步。
4. 本次重启后：三个原受管进程均停止，项目本就没有开机自启。调用日志829次invoking、828次released，最后一条未释放的是14:18:20开始的history；slot0仍active。日志未记录raised/suspended/release_failed，不能将缺少释放等同认证失败，也不能把828次释放宣称828次业务成功。重启后CUA已重新取得钉钉界面，旧两个E108探针可见，未重新发送。

## 下一步及验收边界

沿用户已有恢复指令，先保留本次残留、确认无主，再显式清理调用占位，只启transport；gateway停机期间用同一SQLite快照的watermark≥固定cut且history_window不存在判断补读完成，再停机审查积压，最后恢复原两路gateway。不能再以last_sync.at判断覆盖。未知投递先按原key核账，不重放旧探针/失败任务。

随后用原生UI在AIC测试群和原私聊交办合成任务，核真实工具、原session续接、liev回复、客户端下载打开。认证长期稳定另需自然运行跨刷新窗口观察；不人为改token/时钟、不做锁屏复现实验，也不把恢复成功当根治。所有旧失败、reliability窗口与49/14/1矩阵保留。本轮没有新增产品测试或UI任务通过。

公开源码/issue原文、二进制摘要及本地快照只留local/auth-research-20261113；公开记录见[E111摘要](../evidence/2026-11-13/auth-refresh-reboot-review.json)。
