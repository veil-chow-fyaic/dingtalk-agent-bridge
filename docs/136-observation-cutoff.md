# 新观察的截止采集与证据边界

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->

E136，2026-11-16。修复E135指出的到期只写状态问题；本轮只修改观察工具，没有启动新run、接触业务HTTP/DWS/模型/UI、停止服务或修改调度，旧run不改。23产品模块与E133/E134相同，产品版本仍2467fe2。

## 新run保存什么

`capture_service_observations.py`仍只允许新的run-id，写入`local/service-observations/`。schemaVersion=2，启动以逐路SQLite事务的最大seq建立基线，固定startedAt和cutoffAt，运行时间同时使用单调时钟。每个采样保存本地HTTP结果、产品/采集器/配置磁盘摘要、manager拥有的进程身份及维护journal；不运行auth、doctor或服务启停。

到期、信号或异常退出时自动写`ledger.json`：每路同一个只读事务读取scope、watermark、history_window、最大seq、基线之后的完整事件及delivery状态计数。快照开始/首次读后/结束时间分别保留；运行中的各路数据库没有共同原子时点。失败路写error，后续路仍尝试；SIGKILL无法收尾时保留active或缺seal，不自动修复。

JSON文件先fsync、原子替换并同步目录；采样逐行fsync。最后写`completion.json`，封存baseline/status/observations/ledger/maintenance的SHA。seal能发现文件缺失和变化，不是对抗整体伪造的签名。所有原始证据仅local，不进Git。

## 审查如何拒绝假通过

`review_service_observations.py`对v2强制要求完整seal和截止账本，不因缺失而降级成旧run。固定cut必须等于开始＋时长；每路快照须在cut后5秒内开始、15秒内结束。这个窗口只界定采集容差，不证明cut瞬间内容。缺watermark、watermark未达cut或仍有history_window均不通过；不等待补读后把迟到快照改称截止快照。

基线、路由身份、事件顺序、捕获区间逐内容比对；截止账本尾部尚未被HTTP采样的事件单独计数，不冒充HTTP已观察。版本/配置/采集器改变、进程身份变化、配置与manager记录不符、维护记录或journal变化均使新run截止检查失败；维护不扣除错误。信号、异常、终结写失败与缺尾采样不能成为完整24h。

旧schema v1只保留已有审查语义；本轮没有重审或变更两份旧观察。`observation_complete_24h`只描述记录与截止采集，`zero_recorded_errors`仍独立。当前工具明确`stability_pass=false`、`uniform_loaded_version_proven=false`及`natural_refresh_proven=false`。

## 仍须独立补齐

现manager没有保存进程启动时加载的源码摘要。当前磁盘和PID身份一致不等于进程内已加载相同代码；本轮没有添加无法支撑的“loaded”成功字段。下一独立工作是启动版本来源与采集器核验设计/实现，随后才选择稳定版本、明确维护规则与新观察。还需新的真实24h、自然失效refresh及其余原MUST证据；不能用本轮合成时间推进代替24小时。

## 验证

[脱敏记录](../evidence/2026-11-16/observation-cutoff-validation.json)：冻结源码Python3.14.6及3.11.15分别30方法通过，15新增＋15既有观察专项；不是全量463项或新的wheel安装认证。新增覆盖格式降级拒绝、审查输出不能覆盖原始run、正常到期、缺失/篡改/截断、迟到/过早/慢快照、watermark/续页、错路/第二路失败、并发WAL写、采样事件篡改与账本尾部、版本/维护变化、磁盘摘要不复制配置内容、数据库失败、中断、终结失败、真实子进程SIGKILL。

初轮两处测试错误：空文件截断没有变化、seal末尾空白不改JSON含义；修正测试素材。新增版本测试发现macOS `/var` 与 `/private/var`路径归一问题，函数入口resolve后双Python冻结验证通过。没有以更改判据规避失败。源及日志在`local/observation-cutoff-20261116/final-validation/`。
