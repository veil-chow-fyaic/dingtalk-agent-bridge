# 参与开发

本项目优先把官方 DWS 已有能力接好，只为真实使用缺口补实现。通用 IM 通道和可选执行器分开演进；不把某个测试组织、账号或运行器写成产品常量。

开始前阅读 [AGENTS.md](AGENTS.md)、[当前需求与范围](docs/102-user-requirements-and-roadmap.md)和[任务池](plans/completion/TODO.md)。阶段报告用于追溯，不作为今天的执行指令；现场操作遵循当前会话授权和仓库约定。

## 提交什么

代码改动说明具体触发条件、修改后的用户行为和验证范围。修复实际缺陷时保留最小复现；文档只改事实受影响的部分，不用重复历史测试增加通过数。一个变更可以独立审查时，保持提交小而完整。

账号身份、凭据、会话原文、截图、数据库、下载件和完整运行日志只放被忽略的 `local/`。提交可公开的合成 fixture、脱敏结论和必要摘要；`.gitignore` 不能代替暂存隐私检查。不要运行他人遗留的 `local/` 一次性脚本或复用历史 PID。

当前未选择新的项目许可证。第三方文件继续保留各自许可和来源；不要加入不明来源代码或自行为全仓库授予新许可。远端协作目标确定后再使用其实际 issue/PR 入口，本指南不预设虚构地址。

## 本地开发与测试

在授权检出中安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
```

产品测试使用合成配置和临时状态，不需要真实账号。先运行与改动相关的测试，例如配置/路由行为：

```bash
.venv/bin/python scripts/run_tests_with_evidence.py --pattern test_continuation.py
```

需要全套回归时使用同一入口：

```bash
.venv/bin/python scripts/run_tests_with_evidence.py
```

入口保留合成管理器拒绝证据，报告写入 `local/test-evidence/`；0 个发现用例会失败。测试通过不能替代真实钉钉 UI、模型调用或长期观察；发布验证还须绑定冻结源码、同一 wheel 和实际解释器，见[离线导出说明](docs/144-offline-release-export.md)。

文档改动通常只需相应离线检查。不要为修改文字启动服务、发送消息、运行认证诊断或重复已验收实验。

## CI

[工作流](.github/workflows/ci.yml)在 push、PR 和手动触发时检查文档/manifest/暂存私密边界，运行合成测试，构建 wheel 并核独立安装的模块、许可、元数据和六入口。矩阵为 Ubuntu 24.04、macOS 15 与 Python 3.11/3.14；托管平台实际通过情况以对应 commit 的 Actions 结果为准，不能从本机 macOS 测试推断 Linux 已通过。

CI 不配置业务账号或模型凭据，也不运行真实 DWS、登录或部署。构建阶段需要下载 Python/build 工具；“离线检查”指不连接业务后端，不是整个 Actions 作业断网。Actions 固定完整提交 SHA，依赖更新只提 PR，不自动合并。依赖更新改变受清单保护的文件时，维护者审阅后同步 manifest；不要跳过摘要门。

## 文档与证据

- 新用户流程放[上手指南](docs/getting-started.md)，参数放[接口参考](docs/22-generic-tool-and-consumer.md)，维护流程放[运行手册](docs/15-service-runbook.md)。避免再建一份并行“当前说明”。
- 新文档登记到 `docs/documentation-index.json`，由现有 `render_index` 生成 `docs/INDEX.md`。阶段报告标历史范围并保护正文摘要；账本追加，历史失败不改成成功。
- 原 PRD 判据与等级不随测试结果降低。验收状态有新证据才更新；修改前保存原文，核对判据摘要保持。
- [CHANGELOG.md](CHANGELOG.md)记录用户相关变化；部署、候选、历史通过和未发布版本分别写清。

在工作区完成资料后运行：

```bash
.venv/bin/python scripts/review_documentation.py
.venv/bin/python scripts/review_acceptance.py
.venv/bin/python scripts/verify_handoff.py --write-manifest
.venv/bin/python scripts/verify_handoff.py
```

`review_acceptance.py`只读取声明的覆盖；加 `--require-covered` 会因尚存缺口返回 2，不是产品回归失败。`--write-manifest` 会明确更新摘要账本，须先审阅实际改动。

暂存准备提交的文件后检查：

```bash
.venv/bin/python scripts/verify_privacy.py
git diff --cached --check
git diff --check
```

隐私检查扫描全部暂存 blob；维护者部署环境的已知私有值来自本地配置。无账号检出不能证明识别了所有曾误入历史的秘密，因此导出前仍须独立审阅。未通过的门不要用删失败记录或更改统计绕过。

## 变更说明

描述应让没读过聊天的人理解：问题是什么、行为如何改变、如何验证、还有哪些边界。附准确环境与测试范围，不把专项测试合成全量通过，也不把后续文档 commit 称为实际部署产品。

代码回滚保留当前消息和任务账本；不能用旧数据库覆盖新消息。真实服务维护、未知投递对账、运行器迁移和发布由本轮负责维护者统筹，具体顺序见运行手册。安全问题按[安全说明](SECURITY.md)私下报告。
