# 从 Git 提交生成并核验离线交接包

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E063。现行运行手册原先仍将E054/180项称为当前版本，并遗漏E062退出过渡和新的清理前诊断入口。已在82e1c2a修正文档，改为引用现行状态而不固化易过期计数；历史阶段报告不改。

交接源码固定在完整提交82e1c2af41dd5663f9ead1a57ed8514d901f13f7。使用git archive导出，归档没有.git/local、符号链接或路径越界；其中492项共享manifest在构建前后都匹配，归档内每个文件仍与解包件同字节。此页与后续审计是独立记录，不冒称已包含在该旧提交内。

## 实际验证

先单独从包源准备setuptools84.2.1、wheel0.48.0、packaging26.3，记录各wheel摘要。随后新建构建环境，pip --no-index及本地wheel完成依赖安装和无构建隔离的产品构建；禁用pip版本检查，设置保留但未监听的loopback代理。前置依赖准备不是离线步骤，也不是OS网络沙箱。

新Python3.11虚拟环境用--no-index --no-deps安装新产品wheel，从site-packages导入，运行依赖为空。六入口--help通过；空工作目录dab-service status返回未受管且不创建状态。测试目录只含导出tests/scripts/fixtures，无产品源码或账号配置，197项经诊断入口通过；生成的local只有合成test-evidence。19产品模块与源码、wheel、安装包完全一致。

共16步离线操作和19项只读审计通过。归档及wheel均扫描本机已知私有标识/令牌，未含这些值；原始诊断、安装日志和验证目录不放入交接payload。

## 本地交接产物

local/clean-handoff-20261112/bundle包含source.tar、wheels/、verification.json、audit.json、README.md与SHA256SUMS。仅这些文件是交接payload，父目录还有私有日志，不能整包分享。源码中的docs/15-service-runbook.md说明独立身份配置、官方DWS/图片补充和可选runtime；没有捆绑凭据或远程发布。

创建自己的虚拟环境后，可用下列离线安装形式；路径按实际解包位置替换：

```text
python3 -m venv /path/to/workspace/.venv
/path/to/workspace/.venv/bin/python -m pip install --no-index --no-deps /path/to/bundle/wheels/dingtalk_agent_bridge-0.1.0-py3-none-any.whl
```

本段没有产品改动、服务重启或新消息。只读客户端仍显示原E055回复/文件，没有发现明确新引用入口，未重复菜单或发送。三进程与两路旧记录保持；原观察约13.621h、7不可达，24h未满。Linux、真实失效refresh及剩余UI格子未因此通过；本包仍是未完整验收的实验交付。

```bash
PYTHONPATH=. python3 scripts/accept_clean_handoff.py
```

[构建/源码摘要](../evidence/2026-11-12/clean-handoff-build.json)、[19项审计](../evidence/2026-11-12/clean-handoff-validation.json)。下一段核图片上传补充的独立构建与覆盖边界，不修改官方原版或现场配置。

## E069 当前检查点更新

2026-11-12 10:23。E069已重新导出提交a83d3fd的源码和已验证E068同一wheel；512项冻结manifest、19模块及归档/安装包摘要匹配，无已知私有值。沿用源码与双Python安装包各207项结果，本次没有重跑测试或宣称新部署/UI通过。最新交接payload仅local/handoff-a83d3fd-20261112/bundle；E063旧包保持历史记录。

[本次六项核验](../evidence/2026-11-12/handoff-refresh-validation.json)。当前真实Keychain故障仍未恢复，余下群聊/UI和24h验收未通过；这是一份可保存的检查点，不是完整项目验收。该包固定a83d3fd，此页的更新在后续提交，不能说已包含在包内。

## E075 停机期间的冻结交接更新

2026-11-12。等待单次真实查询许可期间，导出固定提交f0d2911，不包含.git/local或符号链接。539项冻结manifest、全部Python测试与E074隔离测试快照、21模块与E073同一wheel摘要均匹配，8项核验通过，未发现本机已知私有值。沿用E074源码和双Python安装包各244项结果，本次未重跑测试。

最新payload仅local/handoff-f0d2911-20261112/bundle，包含source.tar、原E073 wheel、verification.json、README.txt和SHA256SUMS；各文件摘要已独立重读核对。父目录和其他local内容不能交接，真实查询计划及暂停状态未复制进bundle。原E063/E069归档保持。

[8项核验](../evidence/2026-11-12/handoff-e075-validation.json)。该包是未完成验收的检查点，不能宣称正式发布、认证恢复或UI通过；源码固定f0d2911，本段后写的说明不在归档内。真实DWS调用为0，后台停止，单次核验许可仍待决，不重复询问。
