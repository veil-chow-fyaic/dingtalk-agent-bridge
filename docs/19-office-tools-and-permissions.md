# 组织工具、权限与单人办公验收

2026-11-11，DWS v1.0.67，当前本人 profile。模块帮助和 schema 已归档到 [office-help](../evidence/2026-11-11/office-help)。这是已证实的操作范围，不能推导所有组织或账号都有同样权限。

| 模块 | 已执行的动作 | 实际结果 | 未覆盖与权限边界 |
|---|---|---|---|
| 文档 doc | 本人创建、追加标记、fetch | 标记回读一致 | 他人文档权限、分享、协作、复杂表格未测 |
| 待办 todo | 本人创建、完成、get | completed=true | 他人待办/批量分配未测 |
| 邮件 mail | mailbox list；创建无收件人草稿；+message 按 ID 回读 | 唯一本人邮箱；正文标记相符；to/cc 均空；未发送 | 邮箱开通/访问权是独立条件；真实发送、收件和附件未验收；不需要为本轮提供收件人 |
| 日历 calendar | +book-list；+create；+get | 本人过去时段事件、FREE、无其他参与人；标题时间回读一致 | 创建返回了默认提醒和 onlineMeetingInfo，不能宣称“不会附带会议入口”；未邀请他人、未入会 |
| 会议 minutes | +list-all 只查询 DAB-SOLO-20261111，limit=1 | 调用成功，测试条件返回0，complete=false | 仅证明查询可调用；不证明全列表为空，也未验证正文/转写下载 |
| 钉盘 drive | 对已创建的测试在线文档 +info | 返回成功但提示在线文档元信息可能不准，应走 doc | 不当作普通钉盘文件上传/下载验收；空间、文件 ACL、分享独立核实 |
| 在线音视频会议 | 查看 conference Help/固定版本实现；calendar 响应有会议入口 | 独立 conference helper 标不可用；日程附带会议字段 | 两件事不同；平台目录有音视频 API，不可写成“钉钉不支持会议 API”。会议创建的独立入口、入会、通话、结束、纪要联动未验收 |

## 权限检查顺序

1. 组织管理员在开发者平台开通 CLI 访问；用户 OAuth 绑定目标 corpId:userId。精确流程见 [开通手册](11-onboarding-lessons.md)。
2. 使用同一 profile 执行业务模块只读最小操作；消息、文档、邮箱、日历、纪要、钉盘分别记录成功或实际错误。认证通过不等于业务全授权。
3. 资源必须是本人/明确授权测试对象。模块可列举不等于任意文档、邮箱、会议或空间可读写。
4. 遇到权限错误，记录版本、命令、脱敏错误码、资源类别及上下文；依据该错误或官方 scope 文档列最小管理员步骤。当前没有遇到需补开 scope 的失败，**不编造一份“全选权限”的通用清单**。
5. CLI 帮助元数据是 effect/risk/confirmation 等操作说明，不能当作真实账号权限授予表。schema auth.status 返回未注册是工具元数据缺失，不是账号登录失败；该命令改读 --help。

## 可复用的调用顺序

命令参数须以隔离版本 --help 为准，全部显式 --profile；本机私有引用不写入共享文档。

- 邮件：`mail mailbox list` → 唯一邮箱核对 → `mail draft create`（无 --to、--cc）→ 从 `result.message.id` 取 ID → `mail +message --email … --id …`。本轮未执行 send。
- 日历：`calendar +book-list` → `calendar +create --title … --start … --end … --timezone Asia/Shanghai --free-busy free --yes` → `calendar +get --event …`。回读检查 attendees 中除 self 外为0、时间准确、会议/提醒字段；默认字段也应列入副作用清单。
- 纪要：`minutes +list-all --query DAB-SOLO-20261111 --limit 1`，零结果只代表该测试查询。
- 文档/待办：完整已执行配方与证据见 [实现验收](16-implementation-acceptance.md)，不为了重复验收重新创建对象。

## 本轮新增证据和保留对象

[单人缺口验收](20-gap-acceptance-and-reproduction.md)记录 DOCX/XLSX、多图、文件引用、日程、草稿。精确 ID 在忽略目录 `local/probes/20261111-gaps/`；公开 [结果](../evidence/2026-11-11/gap-acceptance.json)只保存类型和通过条件。

保留一个本人日程和一个未发送草稿供复核；日程为2026-11-11 00:00–00:05 +08:00，标题带 DAB-SOLO-20261111，草稿同前缀。日程含服务端生成的会议入口及默认提醒，未验证实际提醒行为；无他人受邀。之前测试文档保留，待办已完成。后续清理只删除账本中的确切测试对象，不按前缀批量删除业务资源。
