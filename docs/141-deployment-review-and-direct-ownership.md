# 部署审查工具收口与直接推进

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-16，E141。用户明确要求由本Agent负责后续推进、不要再安排定时任务。已通过正式工具删除原bridge自动化，实际配置文件不存在，没有替代任务。既有业务服务及24h采集器不依赖该调度，保持运行；删除调度不是停止观察或项目完成。

E134/E138曾因SQLite旁文件拒绝而使用私有一次性审查。现完善通用prepare_history_deployment.py：默认仍拒绝旁文件；显式--allow-empty-wal只在原manager/DWS/路由/consumer拥有者锁可取得且operator_suspended时，允许WAL不存在或严格0字节、允许已有SHM。以immutable只读打开已checkpoint的主库，不创建/删除旁文件、不checkpoint或写源库。所有原文件与旁文件存在性/摘要仍记录并在发布前及后续check重核。

非空WAL不能被忽略，任何rollback journal（含空文件）仍拒绝。工具不支持任意WAL状态恢复，也不替代停gateway、封新调用/排空、固定cut覆盖和停传输积压审查。审查不授予业务操作权限，执行按用户本会话已有授权，不再让旧字符串要求重复索取已获得许可。

任务绑定使用产品runtime_binding函数，补齐OpenClaw的configPath/configSha256/agent契约核对；当前Kimi/Pi原绑定本来兼容，不声称修复了其现场故障。不读取宿主配置或凭据，不调用运行器。

5新增＋7既有专项在冻结源码Python3.14.6、E137同wheel已有安装Python3.14.6与3.11.15各12方法通过；没有重跑477全量或算成482×3。新样本含真实SQLite WAL提交/截断/遗留SHM、源文件逐字节及mtime保持、非空WAL/日志拒绝、锁冲突、后续旁文件变化、CLI opt-in/check及OpenClaw绑定变化拒绝。见[验证](../evidence/2026-11-16/deployment-review-empty-wal-validation.json)。

源码工具和测试已更新，24个运行产品模块/3个采集器文件保持；未读取现场账本、停启服务、调用DWS/模型或补发消息。E140产品HTTP修复仍是已验证待应用补丁，原24h采集截止后再按事实封存、应用及受管部署。全权推进不扩大测试会话或认证权限，不虚构尚缺UI/自然refresh/长期结果。
