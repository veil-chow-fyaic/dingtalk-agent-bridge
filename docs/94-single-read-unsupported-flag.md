# E082：获准的一次查询因错误参数失败

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


最新状态：E089修正后追加一次已获准成功，两个key都已attempt；后台仍暂停，下一步仅按[待授权E090方案](97-private-chat-recovery-proposal.md)。原E082失败保留。


用户明确允许后，按原key dab-auth-read-20261112执行了一次已准备命令。执行前核无receipt、完整冻结计划匹配、三个manager组件停止和operator_suspended；没有改计划或扩大授权。官方返回exitCode=3、validation/unknown_flag：`unknown flag: --as`。原receipt记failed、attempted=true、automaticRetry=false、targetMatched=false、suspensionUnchanged=true。[脱敏回执](../evidence/2026-11-12/single-read-unsupported-flag.json)。

这是bridge核验脚本的命令准备错误。固定版v1.0.67的chat +conversation-info并不提供--as；先前合成CLI只验证传递和清理，没有用官方命令树校验参数，所以漏掉了它。不能把该错误归给用户、钥匙串或网络，也不能用此前244项通过掩盖真实失败。E073官方办公包装器也追加--as user，需一起核固定官方边界。

本次真实DWS进程调用数为1，之后为0；没有成功取得会话详情，因此认证状态仍未判定。内部可能触达凭据的次数没有插桩记录，不声称绝无钥匙串读取或弹窗。结束后只读复核三个组件仍stopped、暂停仍operator_suspended。没有新UI验收或后台恢复。

原raw-result.json/receipt.json只留local/recovery-checks/dab-auth-read-20261112，保持原字节。原key已消耗，即使失败发生在参数阶段也不得删除attempt、换key或自动重试；用户这一次许可已履行，不包含下一次命令或后台恢复。

下一步只做离线修复：移除不支持的强加参数，保留显式profile固定身份，用固定官方源码的声明命令树对群/私聊核验及六类办公入口进行参数解析测试；不能只更新合成替身期望。原官方checkout/binary不修改，不执行真实CLI --help、auth或doctor。修复及对应验证完成后，才能向用户说明具体下一方案，新的真实调用仍需明确允许。

只读history部署差异/账本清单工具尚在结构设计，未写现场配置；本次授权到达后优先处理唯一获准查询。E080候选仍未应用，可在原核验结束后按原计划审查应用；真实服务继续停止。

## 修正后追加核验提案：待新明确许可

E083已完成官方参数契约修复，E084完整产品三套262项通过，E085本地两路账本清单显示无未完成任务/未确认投递。现已向用户提出追加一次查询，并明确请求允许新的独立记录dab-auth-read-fixed-20261112；尚未答复时不得执行，不重复问。

提案只保存在local/recovery-proposals/fixed-arguments-20261112.json（0600），并不是新的query计划或attempt。其SHA256为18e272f34badf46b8cf8b5a5467f1f4afd330973b77ee3916a78623bfd9e8c7a；冻结当前E084的21模块、E083 checker、相同配置/路由索引、相同官方binary和DWS环境。修正后的命令为同一chat +conversation-info，保留profile/format，移除不支持的--as；限15秒请求＋最多15秒清理。可能仍出现系统窗口，不要求反复输入密码。

只有用户明确允许“追加一次并使用新记录”后，才可根据该提案创建新key的plan，核各摘要完全匹配后执行一次；若新key已有receipt/attempt则仅复核不调用，不得改名继续。原dab-auth-read-20261112的failed/raw/plan始终保留，不覆盖或重置。新许可也不包括后台启动，失败/未知不重试，成功只证明该次会话查询可读。

拒绝或未答复时，继续独立离线工作；没有新真实调用。后台恢复仍需独立说明具体history部署和E085清单并取得明确许可。

## E089：修正后的追加一次已获准并成功

用户明确允许追加一次及新记录dab-auth-read-fixed-20261112后，核提案摘要/当前21模块/正确checker、原失败receipt和三服务stopped；新receipt不存在才prepare匹配计划并执行一次。官方exit0、目标会话匹配，receipt为readable/attempted=true/automaticRetry=false，暂停保持，三服务仍stopped。[7项核验与脱敏结果](../evidence/2026-11-12/corrected-single-read-validation.json)。

本次许可已履行，不再等待该答复或运行此key。E082旧failed保持原字节；两个key都只可复核、不重试/覆盖。此次只证明指定会话的一次凭据支持读取可用，没有证明所有接口、两路后台、长期稳定或UI通过；没有执行auth、doctor、Keychain管理或恢复后台。系统窗口是否出现没有独立观测，不以exit0推断“绝无弹窗”。下一步是明确并冻结history分阶段恢复方案，后台仍需另获同意。
