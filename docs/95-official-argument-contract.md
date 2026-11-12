# E083：官方参数契约修复

E082暴露核验脚本和E073办公包装器错误地向所有命令追加--as user。现移除自动追加，核验查询与六类办公入口只固定显式profile及format=json；办公入口拒绝调用者自行传入--as，避免把不支持的参数或身份变更意图静默吞掉。原DWS负责profile认证，bridge不实现身份/令牌协议。部分聊天发送或event命令仍支持各自声明的--as，不能把它推广为全局参数。

核验脚本新增一个纯参数构造函数，群/私聊各按原目标字段选择参数。已有receipt优先返回旧结果；新回归确认即使代码/计划已改变，failed原key仍只读返回，不会再调用CLI或重写receipt。E082真实attempt及原始响应完全保留，没有准备新的真实核验key，也没有再次执行真实DWS。

## 不再只依赖合成CLI

[固定官方契约fixture](../integrations/dws-contract/README.md)使用v1.0.67 commit 63a7c4906c7dee10750011ea309b9eb78abb7eb0的独立源码归档。测试包放在internal/bridgecontract，避开internal/app的TestMain（后者有keychain清理）。只调用声明命令树构造、Find、默认help flag注册和ParseFlags，不调用Execute/RunE、鉴权钩子、真实CLI、网络或官方TestMain。

从实际bridge函数导出两个合成会话查询与六个办公参数数组。旧八组全部因未知--as失败；修复后八组全部通过。额外遍历六族529个命令声明：518个可解析命令均接受profile/format，拒绝强加--as；11个calendar导航占位因DisableFlagParsing单列，未算解析成功。

初版fixture未注册help flag，六族先返回pflag help sentinel；也把不解析参数的calendar导航占位误认成接受--as。保留两轮原失败日志后修正测试建树方式，最终对同一旧/新argv复核。不能把测试框架问题隐藏，也不能把参数解析通过写成认证或业务调用通过。

## 验证范围

源码与双Python隔离新wheel各254项通过，六入口/21模块及14项审计通过。全量结果、模块/测试摘要及真实attempt原字节核对见[冻结审计](../evidence/2026-11-12/official-argument-contract-validation.json)。全部原始日志、独立官方源码与冻结测试位于local/official-argument-contract-20261112。源码/安装验证针对本次冻结版本，不套用旧E073或E080结果。

本次仅离线代码修复；三个真实服务与operator_suspended保持，新增真实DWS调用为0。E082的一次许可已经用完，原key不可重试/换key；认证状态仍未判定，恢复后台未获许可。下一段可应用已验证的E080历史续页候选并核新整体产品，然后继续只读部署差异与账本清单工具。
