# E081：零测试发现必须失败

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


E080命令编排的错误工作目录使测试发现0项，unittest把空套件视为成功，旧run_tests_with_evidence.py因此也写入ok:true。这个结果从未计入产品通过，但入口本身必须防止再次误报。

当前入口要求实际testsRun>0；空套件或CLI pattern没有匹配时，summary的suitePassed/ok均为false，validationErrors含no_tests_executed，CLI退出1。真实非空执行仍正常通过；原fixture清理前诊断、失败和证据保存错误处理不变。这里不将“所有测试被跳过”改成新规则，范围仅为已复现的0项发现。

[八项核验](../evidence/2026-11-12/empty-test-discovery-validation.json)。新增2方法，旧入口4方法中2失败；修复后源码及E073同产品隔离Python3.14/3.11各4专项通过。实际调用了CLI无匹配路径并核退出码及留存summary，也验证非空实际执行。安装验证显式移除PYTHONPATH、核site-packages中21模块；初次环境未显式清理的记录另留ambient，不混作最终依据。私有原始日志在local/empty-test-discovery-20261112。

只改测试工具与测试，当前产品21模块和E074待决checker不变，没有新wheel或全量重跑。E080的259属于更早冻结候选及旧runner，本次不写成三套261；候选没有0项运行。真实DWS/UI为0，三个服务和operator_suspended保持。
