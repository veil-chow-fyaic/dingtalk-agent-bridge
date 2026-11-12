# E082：获准的一次查询因错误参数失败

用户明确允许后，按原key dab-auth-read-20261112执行了一次已准备命令。执行前核无receipt、完整冻结计划匹配、三个manager组件停止和operator_suspended；没有改计划或扩大授权。官方返回exitCode=3、validation/unknown_flag：`unknown flag: --as`。原receipt记failed、attempted=true、automaticRetry=false、targetMatched=false、suspensionUnchanged=true。[脱敏回执](../evidence/2026-11-12/single-read-unsupported-flag.json)。

这是bridge核验脚本的命令准备错误。固定版v1.0.67的chat +conversation-info并不提供--as；先前合成CLI只验证传递和清理，没有用官方命令树校验参数，所以漏掉了它。不能把该错误归给用户、钥匙串或网络，也不能用此前244项通过掩盖真实失败。E073官方办公包装器也追加--as user，需一起核固定官方边界。

本次真实DWS进程调用数为1，之后为0；没有成功取得会话详情，因此认证状态仍未判定。内部可能触达凭据的次数没有插桩记录，不声称绝无钥匙串读取或弹窗。结束后只读复核三个组件仍stopped、暂停仍operator_suspended。没有新UI验收或后台恢复。

原raw-result.json/receipt.json只留local/recovery-checks/dab-auth-read-20261112，保持原字节。原key已消耗，即使失败发生在参数阶段也不得删除attempt、换key或自动重试；用户这一次许可已履行，不包含下一次命令或后台恢复。

下一步只做离线修复：移除不支持的强加参数，保留显式profile固定身份，用固定官方源码的声明命令树对群/私聊核验及六类办公入口进行参数解析测试；不能只更新合成替身期望。原官方checkout/binary不修改，不执行真实CLI --help、auth或doctor。修复及对应验证完成后，才能向用户说明具体下一方案，新的真实调用仍需明确允许。

只读history部署差异/账本清单工具尚在结构设计，未写现场配置；本次授权到达后优先处理唯一获准查询。E080候选仍未应用，可在原核验结束后按原计划审查应用；真实服务继续停止。
