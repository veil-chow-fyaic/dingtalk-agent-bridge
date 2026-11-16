# Codex部署与真实私聊验收 E120

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


产品0c6f2da已部署，AIC群保持Kimi，原veil/liev私聊切换为Codex0.164.0。三服务运行、DWS ready；这次闭环检验了真正的钉钉用户输入、普通账号liev回复和文件下载。身份不变，无新bot。

## 用户结果

| 原生客户端动作 | 实际执行及客户端结果 |
|---|---|
| veil私聊新任务 | Codex执行Python31×59=1829，检查持久网络变量存在而不输出值；liev文本/JSON可见，env_ready=true |
| veil沿用当前会话 | 实际读取前一JSON，再加7得1836；同Codex session，TXT回传 |
| 下载两份附件 | 均从钉钉保存至local，Finder Quick Look打开显示正确正文；42B JSON和34B TXT与原件SHA一致 |
| veil启动延迟任务、再发/agent cancel | 原生Python先写起始时间再sleep90；客户端显示“已请求停止当前任务”“任务已停止”。工具起始104秒后无late，捕获的4个自有后代均退出，guard记录sent_and_exited |

89旧任务/旧outbox保留；新增2完成工具任务、1取消工具任务、1完成控制任务；9回复confirmed并由history回读。群旧任务/session保持。30项核验通过，详见[脱敏证据](../evidence/2026-11-13/codex-deployment-ui-validation.json)。E119同一冻结源码及wheel的374×3回归为此产品证据，不混比后续文档HEAD。

## 部署与失败保留

先停空闲gateway、封新DWS调用/排空并停transport，保存六库；显式binding迁移原私聊，Kimi会话已通过原生new归档。固定cut补读、停止并审查零新积压后启动。首次启动DWS返回api/request_timeout，3.87秒，providerExecutionStarted=false；没有认证错误，不能说是token过期或Keychain又坏了。该次失败留原位，未触发auth/doctor。相同环境配置下一次有界恢复成功，再补读/停机核账后启动；没有自动循环重试。

E118取消返回后约90秒late反例保留，不能被本轮新成功改写。E119取消先由官方CLI处理SIGINT/turn interrupt，再有限进程组清理；清理范围不是OS沙箱。私聊任务timeout仍60秒，未通过扩大超时凑结果。

原24h观察aic-persistent-env-20261113保持同run，记录真实维护、启动失败及开发时旧gateway/候选guard混用区间；不能称同版本连续健康24h。系统最初Keychain根因及自然刷新仍未证明。剩余49/14/1、七项MUST缺口不变；Pi/OpenClaw未验，不外推已支持。

## 后续与回滚边界

下一步剩余消息协议的新官方/UI入口；无新入口转当前版干净检出/安装/许可/回滚交接或下一runtime契约。禁止重发E116/E120样本。回滚先按归属停服务，保留当前session/tasks/outbox；恢复模块必须与目标wheel对应，运行器变更需要用户任务new归档及显式binding迁移，不能直接改runtime配置绕过绑定。旧Kimi原session归档与当前Codex session均须保留。私有精确计划/六库及全部UI原件位于local/codex-native-interrupt-20261113，不能作为公开交付包。
