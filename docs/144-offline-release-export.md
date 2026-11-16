# 离线交付包导出

`scripts/export_release.py`从显式Git提交导出源码，并绑定已经验证的wheel。它不构建或重新运行产品测试，不读取`local/`账户配置、令牌或数据库，不操作当前服务。原来的阶段审计脚本仍用于其各自历史证据。

先完成当次冻结源码/同wheel验证，把脱敏验证JSON写入`evidence/`，按现有文档、manifest和暂存隐私门完成本地提交。然后执行：

```bash
python3 scripts/export_release.py \
  --repo /absolute/path/to/dingtalk-agent-bridge \
  --commit <已提交的完整commit> \
  --wheel /absolute/path/to/dingtalk_agent_bridge-0.1.0-py3-none-any.whl \
  --validation evidence/<日期>/<验证文件>.json \
  --output /absolute/path/to/new-bundle
```

输出父目录须存在，输出目录须不存在。工具固定commit及tree，只读取Git对象；工作树中未提交/未跟踪文件不进入包。文档可以比被测产品晚提交，但导出包内所有产品模块、许可及其他资源必须与wheel完全相等。不能将新代码配旧wheel，或用工作树的验证JSON替换所选提交中的证据。

所选提交必须具有完整、准确的`evidence/handoff-manifest.json`。验证JSON支持E140格式的`candidateWheelSha256`/`validation`，以及当前冻结验证的`wheelSha256`/`codeSha256`/`results`。必须绑定同wheel SHA，所有测试行`ok=true`、`exitCode=0`、`testsRun>0`，有唯一的`source`、`py314`、`py311`三环境记录。给出的模块摘要、安装隔离或包一致性结果也必须匹配/通过。工具核对已提交的声明与产物绑定，不独立证明记录中的测试真正执行过。

wheel全量payload、RECORD、包版本、Python约束、运行依赖、入口与pyproject逐项核对。当前只接受本项目无运行依赖的py3-none-any wheel；不支持未知额外包、链接或特殊文件。

成功目录包含`source.tar.gz`、wheel、`README.txt`、`CHECKS.json`、`SHA256SUMS.txt`和`COMPLETE.json`。所有内容核对通过后才创建新输出目录；写入失败时保留不含完成标记的部分目录，不覆盖或复用它。完成标记在全部文件落盘后原子发布。使用前核对完成标记指向的CHECKS/SHA256SUMS摘要和每个工件的校验和。

工具拒绝私有运行根目录、凭据目录、符号链接及私钥标记，但不读取真实凭据建立扫描词库，不能保证识别已误入Git的所有身份值或秘密。发布前仍须执行项目原有暂存隐私门。公开合成图片等fixtures按manifest允许；与仓库隐私门一致，.sqlite/.sqlite3/.db数据库路径即使已入manifest也拒绝。

安装者使用包内已验证wheel离线安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-index --no-deps ./dingtalk_agent_bridge-0.1.0-py3-none-any.whl
```

解开源码归档后按`docs/15-service-runbook.md`和配置模板接入自己的官方DWS与已授权会话。DWS二进制、账号授权及可选模型凭据不随包交付。CLI/HTTP/consumer可以独立运行，gateway可选。回滚代码须保留当前账本并核运行器/配置兼容性，不以旧数据库覆盖新消息。该包始终标明`fullProductAcceptance=false`；打包校验不替代长期、UI或所有MUST验收。
