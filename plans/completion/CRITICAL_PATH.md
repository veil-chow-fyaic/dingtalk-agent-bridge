# 当前关键路径

E107当前（2026-11-13）：三个进程running，但DWS调用已持久暂停（dws_process_interrupted，闩mtime09:33:56），两路history有未完窗口，远端积压未知。不得称正常收发，不自动清闩/恢复或要求密码；先补只含调用类别/归属/阶段的诊断并用合成中断验证。E104候选c5ee1fe未部署；E105 Codex60秒仍超时；E106205采到事件与旧账本一致但不证明原截止全量。CUA两次图像错误路径停止，心跳PAUSED。 [当前证据](../../docs/110-interrupted-history-current-state.md)。

E104新增（2026-11-13）：C03能力/终态和C04会话兼容性已实现，旧冻结4负例复现，24新增方法，冻结源码/同wheel双Python各331和13核验通过；详情[运行器契约](../../docs/107-runtime-and-session-contracts.md)。当前候选未部署，真实gateway仍E099。CUA正确bundle连续两次failedToCreateImageDestination，停止该路径；不得称新UI通过。旧session须按已加载版本/原配置审查后显式迁移，不能自动重置/重放。

E103历史检查点：E102回执一致性已部署transport，E099结果契约已部署gateway；固定源码/同wheel双Python307，实际群任务1387及15核验通过。49/14/1、7 MUST未完整，判据不变。详情见[当前任务](CURRENT_MISSION.md)、[E100](../../docs/104-aic-group-long-text-and-controls.md)、[E102/E103](../../docs/106-send-evidence-contract.md)。

## 下一段

0. E107优先：受管调用暂停，归属/中断阶段证据不足；只读核账和合成故障补诊断，不自动恢复或认证。保持原history_window，远端积压未知；原UI/Codex失败路径无新证据不重复。

1. E104 C03/C04候选已实现，冻结源码/同wheel双Python各331和13核验已通过；部署需核旧gateway配置/版本及空闲账本，备份后显式迁移同一原session契约，不能用当前配置猜未知历史。CUA绑定连续两次图像错误已停止，工具恢复后再部署/真实任务UI，不盲发。
2. Codex独立诊断：先读已有私有失败日志及固定CLI/环境差异，CEO只作线索；不重登录/拷贝凭据/改HOME/只扩大超时。真实任务UI闭环后才声明第二运行器支持。Pi/OpenClaw逐个接同一接口，不重造通道、不同时启动双执行器。
3. 14 blocked与1partial涉及原生协议/引用/组合。只沿明确的新官方/UI入口测试，旧失败路径loop guard保持；不能把文件形态当原生协议，不能擅自降低MUST。
4. E106采到205事件已与后续账本精确匹配，原观察四文件SHA不变；窗口截止缺入库时间无法追补、版本记录不全，当前AIC长期覆盖仍缺。不要重复这205条核验；新观察须独立保留版本/终止时账本，不抵消旧故障。
5. 当前版干净检出、许可/模板/运行回滚文档、最终交接及14 MUST/64格一致审查；E075旧包仅历史，全部满足才完成。

## 保持

只有新AIC群及原两人私聊可实测，企业大群/旧群禁止；不加人/bot/权限/远程发布。三服务运行、心跳PAUSED，不重复恢复。auth/doctor/系统Keychain等禁止；正常受管业务固定官方身份，两并发/90+15秒，history-only15秒，不杀共享bus。

E098媒体和E100长文/控制已过，不重发。E102 C02负例已修复并E103真实正向验证，不重跑旧负例凑数量。未知投递原key核对，失败/取消/拒绝保留，两个历史一次查询key不再调用。记录在原分支小步提交，私有原件不入Git。

E105：Codex 0.164.0完整start/resume参数解析通过；一次新60秒本地任务仍request timed out，守护清理完成、无工具/产物/IM。无根因结论，不重复同路径或扩大超时；需新环境/服务证据再推进。见[诊断](../../docs/108-codex-cli-timeout-diagnostic.md)。
