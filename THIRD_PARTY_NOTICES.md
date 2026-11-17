# 第三方材料与许可声明

项目根目录的 [MIT 许可证](LICENSE)适用于本项目原创内容，不替换第三方材料的原许可证、版权通知或已有明确的文件级许可声明。下面列出随本仓库提供的第三方来源及其适用范围；仅引用、研究或调用某个项目，不表示已经复制或分发其完整代码。

## CEO Agent Service

- 来源：[`callzhang/ceo-agent-service`](https://github.com/callzhang/ceo-agent-service/tree/bd3de36b136abfd5e3dc571347358ea5b1be69c1)，固定提交 `bd3de36b136abfd5e3dc571347358ea5b1be69c1`。
- 范围：`dingtalk_bridge/core.py` 中从 `DingTalkFileHandler.dispatch` 改造的发送前摘要校验逻辑；完整业务 handler 未导入。采用范围见[原记录](docs/references/artifact-digest-adoption.md)。
- 许可：MIT。原版权与许可全文保留在 [ceo-agent-service.txt](dingtalk_bridge/licenses/ceo-agent-service.txt)，并随 Python wheel 分发；原文件 SHA-256 为 `aa701f916a7668c604baf6a7e15650090b45d023157ce662ff5b9e2d41db5f85`。

## DingTalk Workspace CLI

- 来源：[`DingTalk-Real-AI/dingtalk-workspace-cli`](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/tree/63a7c4906c7dee10750011ea309b9eb78abb7eb0)，固定版本 v1.0.67，提交 `63a7c4906c7dee10750011ea309b9eb78abb7eb0`。
- 许可：Apache-2.0。仓库已有[上游 LICENSE 原文](evidence/2026-11-13/dws-cancellation/LICENSE-DWS)，SHA-256 为 `1d951e8ca1019e1ad6fc14b8450df1b7ba788b9f242002873ca79df70ee376fd`；另有[早期探针随附许可](evidence/2026-11-12/dws-keychain-timeout-probe.LICENSE)。固定版本的[上游 NOTICE 原文](evidence/2026-11-13/dws-cancellation/NOTICE-DWS)一并保留，SHA-256 为 `b7d8a7d7c3c61cb0d4d78fa422fb81028c76d0e7ff1a23b1be68f058a9920d80`，对应官方 Git blob `d6e564b6adda21dcbcaf5a022791fda014a86742`。
- 随仓库提供的上游上下文/改编材料：`docs/patches/E117-dws-cancellation.patch`、`docs/patches/E145-dws-integration.patch`，以及标有 Alibaba 版权与 Apache-2.0 的 `evidence/2026-11-12/dws-keychain-timeout-probe_test.go`。补丁表示本项目的变更，不是官方已发布的修复；来源和修改范围见[固定清单](evidence/2026-11-13/dws-cancellation/source-pins.json)。这些材料中的上游内容保持其 Apache-2.0 许可。
- 图片上传[补充源码和测试](integrations/dws_image_upload/README.md)编译到固定 DWS 源码中，调用其已有 helper；本项目原创补充不重新授权上游实现。构建出的组合产物需继续保留该上游及实际包含依赖的许可和通知，不能仅附本项目 MIT。
- NOTICE 按固定上游原件完整保留，其中提到的 AI Card/A2UI、SafeChat/OpenSSL、Unicode、regexp2 等说明属于上游产品。保留该原件不表示本仓库另行分发这些组件、静态库或完整 DWS 二进制。本项目 Python wheel 不包含 DWS；若以后分发组合二进制，应按实际产物另核其完整第三方材料。

## go-keyring

- 来源：[`zalando/go-keyring`](https://github.com/zalando/go-keyring/tree/v0.2.8)，固定版本 v0.2.8。
- 范围：`docs/patches/E117-keyring-cancellation.patch` 与 `docs/patches/E145-keyring-integration.patch` 包含该项目 Darwin 实现的上游上下文及本项目修改；未在 Python wheel 中打包 go-keyring。
- 许可：MIT。原版权与许可全文保留在 [LICENSE-go-keyring](evidence/2026-11-13/dws-cancellation/LICENSE-go-keyring)，SHA-256 为 `14bc00f1a298eb6af250216b9e60027a4386c8a84fa2c7ddc2b5c10908e06d0d`。固定来源/文件摘要见[清单](evidence/2026-11-13/dws-cancellation/source-pins.json)。

## 文件级声明及研究引用

`evidence/2026-11-13/dws-cancellation/dws_candidate_test.go` 与 `keyring_candidate_test.go` 已有明确的 `SPDX-License-Identifier: Apache-2.0`；保留其现有声明，适用许可全文见同目录的 [LICENSE-DWS](evidence/2026-11-13/dws-cancellation/LICENSE-DWS)。项目根 MIT 不将这些文件重新许可。

[参考目录](docs/references/catalog.json)中的来源记录、URL、接口研究与摘要，不等于导入所引用项目的完整实现。未确认许可或标为 `UNLICENSED` 的参考没有因此获得复制授权；未来引入实际代码时，应逐文件更新来源、许可、通知及打包范围。构建工具下载的依赖仍应保留各自许可，不由本声明统一改为 MIT。
