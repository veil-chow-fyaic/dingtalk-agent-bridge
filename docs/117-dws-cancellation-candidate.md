# DWS Darwin取消缺口：双层候选与合成回归

2026-11-13，E117。基于固定DWS v1.0.67和go-keyring v0.2.8，已形成两份最小源文件候选、可重复执行的离线工具和上游报告草稿。**尚未应用到官方CLI或bridge现场，不是系统钥匙串根因修复，也不是可直接合入上游的完整PR。** 产品仍为87a3d39；24h观察沿用原run，没有重启或重置。

## 缺陷与改动

[E094](99-dws-base-failure-diagnosis.md)已复现：官方worker超时只结束等待，实际无context的子进程继续运行；default-keychain预检查还在预算外。此次只处理这个独立缺口，不触碰真实登录、存储、Keychain或系统服务。

| 层 | 候选行为 | 合成证据 |
|---|---|---|
| [DWS补丁](patches/E117-dws-cancellation.patch) | 从预检查前创建一个deadline，传至get/set；超时另留有限清理期，worker未退出明确返回cleanup pending；迟到结果不作为成功，不在已取消读取后再写 | 成功、不存在/不可用分类、panic、预检查/读/写三种子进程卡住、同一deadline、迟到成功、不配合退出与禁止迟到写入 |
| [go-keyring补丁](patches/E117-keyring-cancellation.patch) | Darwin专用GetContext/SetContext；CommandContext和WaitDelay把取消传至本调用的进程；Set改用Run完成stdin/Wait回收；超长参数在创建进程前拒绝 | raw/base64/hex解析、不存在及exit51分类；Get/Set实际合成子进程终止/回收；stdin及提前退出、超长/已取消写不启动 |

静态审查还发现依赖旧Set在Start之后才检查4096字节限制，超长或stdin错误分支可直接返回而不Wait；候选把校验移到启动前，并把写入/等待交由Run。它仍使用原有`add-generic-password -U`及编码/引用方式，没有改变存储身份或加密政策。

命令取消只针对当前调用创建的子进程。它不能撤销已经完成的写入、系统已经排队的授权窗口，也不证明无法杀死的内核进程必然在墙钟期限内回收；worker不配合时必须承认清理未完成。不触碰官方共享Setsid bus。

## 验证范围与复现

固定来源和每个编译文件/补丁/测试的摘要见[source-pins](../evidence/2026-11-13/dws-cancellation/source-pins.json)。DWS原commit为`63a7c4906c7dee10750011ea309b9eb78abb7eb0`，Go为本地1.26.7；uuid依赖固定v1.6.0。参考checkout、Go模块缓存及原官方binary不改写。

[验证报告](../evidence/2026-11-13/dws-cancellation-candidate-validation.json)：DWS **10方法/3子用例**、keyring **5方法/7子用例**，普通及race模式四次均通过，每套有1个仅供子进程启动的helper正常跳过。共15个独立测试方法，不把父测试/子用例或race重复算成产品新增测试。另18项核验包括摘要、许可、错误补丁拒绝、目录保护、空/缺项/失败测试报告拒绝与现有21产品模块不变。初版直接构造与最终公共工具复现日志都留local，公共报告只引用最终同字节版本。

公共[复现工具](../scripts/check_dws_cancellation_candidate.py)先核所有输入摘要，只向新的`local/`子目录复制选定源码，精确应用补丁；禁止下载、现有目录覆盖和模糊补丁。输入目录参数由复核者提供，例如：

```sh
python3 scripts/check_dws_cancellation_candidate.py \
  --dws-source "$DWS_SOURCE" \
  --keyring-source "$KEYRING_SOURCE" \
  --uuid-source "$UUID_SOURCE" \
  --go "$GO_BINARY" \
  --output local/e117-reproduction \
  --race
```

三个source参数指向已取得且与pins相符的源码目录，go参数指向本地Go 1.26.7工具链；首次输出目录必须不存在。结果和原始编译/测试日志只落该目录。它不是下载/安装/部署脚本，也不含DWS调用。

测试只编译5个官方keychain文件、必要keyring/uuid源文件和两份明确的新测试；不运行官方完整TestMain或全套存储测试。DWS默认后端全部改为fail-closed测试钩子，keyring命令钩子仅启动当前测试binary，模拟错误字符串及exit51，没有执行`security`。合成子进程可验证退出/回收，不能验证OS授权交互。旧套件的10/5方法直接构造通过后，最终工具在新的目录以同摘要源码重建再执行；并未重跑357项bridge产品测试。

## 上游集成前仍需处理

1. 依赖增加的是Darwin专用API，正式集成需维护者决定跨平台接口或内部adapter方案及发布版本；DWS当前公开依赖还没有这些API。
2. DWS原测试钩子和wait函数签名需随context调整；本报告不声称原测试全集或CLI整体编译已通过。普通读写/错误分类的合成回归通过，不替代完整迁移和平台回归。
3. 保留原逻辑的风险仍在：无效已存DEK被视为missing、`-U`并发替换语义、成功Set但读回失败时的原fallback，均未纳入此次取消修复，不宣称“仅在已证实空槽才写”。Delete/DeleteAll也未改为context版本。
4. 只有候选被审查、同版本全量构建和回归完成后，才讨论隔离验证/升级；当前不替换官方binary、不将候选注入真实凭据环境、不撤销bridge外层保护。

[上游报告草稿](118-dws-cancellation-upstream-draft.md)仅保存在本地Git，未发布issue/PR。D01系统根因仍unknown；D02现为“独立缺陷已复现、候选通过合成回归、尚未上游集成或部署”。R13等验收缺口没有因此关闭。
