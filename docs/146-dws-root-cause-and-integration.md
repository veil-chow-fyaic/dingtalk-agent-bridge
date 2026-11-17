# DWS钥匙串故障分层与完整取消修复候选

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->

2026-11-17，E145。实际bridge仍为2b479a8、官方DWS仍为固定v1.0.67。本轮补齐DWS取消候选的完整源码集成、构建和跨层验证，以及E144图片配置候选的Python3.14安装缺项；没有现场维护、升级、真实认证/Keychain操作或新增消息。

## 原故障为什么涉及钥匙串

官方Darwin实现把登录态加密写到文件，把解密用的DEK放在macOS登录钥匙串。正常业务先读取DEK，才能恢复认证材料并请求API。E094既有系统日志已证：屏幕密码解锁后，登录钥匙串解锁返回SecKeychainLogin=-25293，随后DWS读不到DEK、退出51；普通终端也失败。系统故障起点已定位，最终触发原因仍未知。同期Computer Use Guardian活动只有时间关联；用户重启/重登后业务恢复不能证明永久根治。

截至本轮，[Codex #60687](https://github.com/openai/codex/issues/60687)仍open，未取得官方确认本机因果或修复版本。DWS[最新稳定v1.0.68](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.68)及main的Darwin源码仍与固定v67同字节，不能承诺升级即解决。[#1132](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/issues/1132#issuecomment-5762379764)维护者确认的v62刷新槽位修复属于另一问题。完整OAuth支持自动续期，没有每日重新登录的设计要求。

本机现有止损是明确分类、最多两并发、90秒调用及最多15秒清理，已识别凭据故障等触发持久暂停。此前未及时隔离后台调用又做锁/解锁，放大了弹窗，是处置错误；现在不再用login/doctor/密码/锁解锁反复试错。系统根治仍需适用的官方修复证据；独立执行环境只是未实施、未验证的备选，不能靠同机换终端宣称隔离。

## 本轮真正补完的源码缺口

D02是独立可复现缺陷：官方worker超时只结束等待，底层keyring命令仍可能运行，预检查还在预算外。E117已有选定文件候选，本轮没有修改其历史记录，新增[完整DWS补丁](patches/E145-dws-integration.patch)和[依赖补丁](patches/E145-keyring-integration.patch)：

- 固定v67完整git archive；DWS以相对路径连接同级keyring目录；三个原测试文件迁移context签名，原断言保持。
- 预检查/读取/写入共享单次本地deadline，取消传至本调用创建的子进程并Wait回收；迟到成功不能盖过取消，未能清理如实报pending。没有把CLI根context接入所有层级，也不承诺撤销系统已排队窗口或已完成写入。
- 两个产品Go文件与E117已测候选同字节；依赖最低Go声明改为1.20以匹配WaitDelay。实际只验证Go1.26.7/Darwin arm64，不宣称其他工具链/OS通过。
- 完整CLI构建通过，两份原测试文件集合均编译通过；三个编译产物未执行。运行使用隔离fail-closed测试入口，不执行原TestMain、真实security或原依赖Get/Set/Delete/DeleteAll测试。
- 17个DWS方法（5个原mock/path、10个E117、2个新跨层）及5个keyring方法，普通和race模式分别通过；是22个不同方法，不按模式算44个新方法。新跨层测试接通DWS worker→实际patched keyring→合成子进程，验证正常读/创建调用顺序与取消/回收，不代表真实OS存储写后读回。

公开补丁采用零上下文格式，须在上述固定来源中用`git apply --check --unidiff-zero`及`git apply --unidiff-zero`应用，并核结果摘要。Go制表符上下文会被仓库文本diff门误读为空格缩进，故只转换补丁表示，未修改候选源码。

独立Agent审查及主Agent从干净来源重建补丁通过。原签名迁移失败、最低Go声明修正前记录均保留；主审首次副本继承缓存只读目录导致patch失败，改在新的自有可写副本重建，原缓存及现场未改。

现有invalid-DEK视missing、-U并发覆盖、Set后读回fallback、Delete/DeleteAll政策保持；这些不是本轮取消修复的范围。正式采用仍需相应依赖/API/版本决策及真实环境验收。本轮是可构建、可复核的完整源码候选，尚未替换官方程序或发布上游。私有reproduce.py只做了语法检查，实际成功命令及日志另存，不能把包装脚本称为又一次成功复现。

## 近期约3秒错误与恢复

E144保存窗口中的31次history错误是30次API request_timeout及1次未分类，3.266–3.473秒；没有受管90秒进程超时或凭据暂停。31次错误后两条路由均出现新的完整同步并清除错误，最长观测上界47.764秒。安全审计没有逐attempt路由字段，不能把紧邻另一条路由成功当同路成功；该上界也包含采样延迟。

固定源码有3秒DialContext，但统一超时分类不足以定位DNS/TCP/代理/TLS/服务端；不会凭耗时认定钥匙串或刷新故障。后续原history只读轮询可继续，未知发送仍不得重发。手册已修正“所有超时都要人工resume”的过宽表述。原24h固定cut与零错误false保持，截止账本、自然refresh未证。

## 同步完成的交付准备与UI现状

E144同一个73f0d5c4…64813 wheel新增独立Python3.14安装验证：2新增＋9相关既有方法通过，site-packages及25模块匹配；3.11同范围已过。准确声明源码2、安装3.14=11、安装3.11=11，已通过现有部署/导出验证记录解析器；不是504/506全量。维护/回滚清单与空白执行回执已备，产品源码仍未应用。

用户确认的是手动钉钉客户端正常。本轮据新条件实测：应用可识别为running，但CUA窗口读取仍返回-10005/failedToCreateImageDestination，未留下可用句柄。未做原生点击/输入或重发；E134原两条组合定位/四原件摘要和私聊入站引用安全草稿准备留local，自动化UI验收仍未完成。

5 MUST与51/11/2不变；当前运行观察继续到北京时间11月17日18:29:37，原证据不重置。细节见[脱敏验证](../evidence/2026-11-17/dws-full-integration-validation.json)及[图片候选安装记录](../evidence/2026-11-17/configure-image-install-validation.json)。
