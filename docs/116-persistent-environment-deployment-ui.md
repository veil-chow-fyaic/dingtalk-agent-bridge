# 持久配置部署后的群与私聊真实验收

2026-11-13，E116。产品 **87a3d39** 已由原manager部署，群范围仅AIC测试群，私聊仍veil/liev。没有认证、系统钥匙串、权限或全局DWS改动。固定DWS v1.0.67、history-only 15秒、显式真人profile保持。

## 部署实际经过

先核86条旧任务及投递均无待处理项，按归属停止空闲gateway；封新DWS调用并等在途槽释放后停transport。保存六库快照、旧配置/manager归属和原session。将已有、前轮实测有效的网络条件写入两份私有runtime.environment配置；transport配置原字节不变。

启动进程主动移除HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/NO_PROXY及其小写变量，用它拉起新版transport。只补读历史，gateway不执行。持久watermark覆盖本次固定cut且history_window为空后，再封新调用、排空、停止transport。停机审查11项通过，原任务/inbox/旧事件和回执保持，0未消费本地事件、0待审任务。随后从同样无代理变量的启动进程恢复三服务；两份持久配置成为Agent网络环境来源。

这次重启的是项目受管进程，没有重启Mac、没有开机自启服务，也没有更换原session或重放旧失败任务。

## 真人用户视角验收

通过原生钉钉UI，以veil发送两个明确的新任务；liev普通真人账号通过DWS回复，客户端显示“通过AI发送”。没有借用UI补发API不明消息。

| 会话与任务 | 实际执行证据 | 客户端结果 |
|---|---|---|
| AIC，E116-G | 原session中实际Bash→Python，读取旧文件new_result=1517，计算43×47=2021；实际读取网络变量，只输出布尔检查结果 | liev接收、完成文字和47B TXT可见；从钉钉下载后Quick Look显示1517/2021/env_ready=true |
| 原私聊，E116-D | 原session中实际Bash→Python，读取旧JSON的1003，计算19×61=1159；相同环境检查 | liev接收、完成文字和68B JSON可见；钉钉下载后Quick Look显示1003/1159/env_ready=true |

两份产物均以实际工具输出和下载件校验，不以模型自述代替。客户端下载件SHA256分别与runtime冻结产物及发件箱摘要一致。六条新回复全部confirmed，并在官方history回读为自身消息；未产生额外任务。86旧任务、旧回执、两原session/契约/generation均保持。本轮38项部署/UI/账本核验全部通过，详见[脱敏证据](../evidence/2026-11-13/runtime-environment-deployment-ui.json)。聊天、截图、完整日志、配置和六库只留local及私有CUA记录。

新代码的实际DWS调用已生成结构化诊断：截止本次审计58个result，含44次history、6次send、6次send_status及2次会话初始化，均有exit/耗时/阶段，没有观察到错误。这个计数是短时样本，response_ok不代替投递回执，也不是24h或自然刷新成功证明。错误分类负例来自E115的合成测试，未在真实账号上故意破坏认证或制造超时。

## 当前结论及下一段

**运行环境持久配置、DWS安全错误信息及此次部署后两路真实任务/文件UI已闭环。** E115冻结源码/同wheel双Python各357项与本次产品21模块一致；测试/部署版本分别明确。最初Keychain故障根因没有因此解决，官方取消缺口、跨设备稳定性、自然刷新和完整长期验收仍开放。

[当前独立观察](../evidence/2026-11-13/runtime-environment-observation-start.json) `aic-persistent-env-20261113` 已实际启动：24小时上限，每30秒只读loopback health/events。启动时另存本次21模块摘要、配置摘要/原值私有记录、manager归属和六库基线；旧reliability-20261111不改写。后续维护或代码切换必须记时间和加载版本，离线/失败保留；到期还需截止账本核对，不能自动标健康或项目完成。自然刷新目前unknown，不读取token猜测。

接下来在观察期间推进官方取消缺口的合成候选、剩余协议的新入口及Codex新环境诊断；旧路径loop guard保持。64格49/14/1、7 MUST未完整不变。心跳继续ACTIVE，项目未完成。

原bridge心跳已通过官方automation工具同步到E116并读回核对，继续每30分钟；明确M1/M2完成、观察run已存在及下一独立项，避免下次重复部署或重复验收。
