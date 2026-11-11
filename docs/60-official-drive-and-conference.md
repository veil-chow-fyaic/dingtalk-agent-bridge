# E043：官方钉盘与会议边界

2026-11-12；仅指当前固定DWS v1.0.67及已绑定liev profile。官方源码checkout的精确tag为v1.0.67；不把本机命令存在或read成功外推为全流程可用。证据official-office-boundary.json覆盖8项核验，原始help/schema/只读回执只在local/office-boundary-20261112。

## 会议不是一个统一能力

| 类别 | 本版本契约与当前实证 | 接入处理 |
|---|---|---|
| 独立视频会议 | conference为隐藏兼容入口，源码直接返回不可用、不调用后端；本机调用退出5，错误明确该产品已从开源CLI下线 | 当前官方CLI直接发起、邀请入会、会中控制阻塞；没有擅自创建会议、改权限或装插件，亦不推断所有钉钉API均不可用 |
| 日程附带在线会议 | calendar event create/update支持add-online-meeting；创建默认由服务端附带，更新true会覆盖会议，false保留既有会议 | E021日程返回会议字段已单列；不能算独立视频会议操作/真实入会验收 |
| 实体会议室 | calendar room为日程的资源参会人；location仅文字地点 | 需真实room ID及场景授权，不能用填写地点冒充预订 |
| AI听记 | minutes有上传/转写/摘要/行动项/下载；upload-and-analyze可用既有taskUuid恢复等待 | 本次本人DAB关键词搜索成功且完整返回0；未上传分析、未录音，不能当成独立会议或原生语音条 |

固定版官方来源：[conference源码](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/conference.go)、[calendar指南](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-calendar/references/calendar.md)。会议缺口已有具体平台/版本原因，无需自研虚构会议API。

## 钉盘、文档空间与IM文件

官方drive +upload负责普通文件上传与读回，+download负责实际下载本地字节；无需bridge重造上传事务。钉盘目标使用space-id/folder；文档空间使用workspace，二者不是同一种ID。mySpace是本人“我的文件”，myWikiSpace是“我的文档”；默认wiki space list会查询组织知识库，不能依赖默认值选择私人目标。

本次以显式profile实际查询mySpace成功，获得唯一的本人空间及根目录。drive +find-file搜索DAB还返回了既有合成ALIDOC节点，说明搜索结果须检查type，不能把命中项全部按普通文件下载。此前原件上传到IM、下载IM资源，不等于已在钉盘中建立文件。

官方上传schema的idempotency为unknown，读回验证不能制造服务端幂等；若创建回执不明，保存原意图和原响应再对账，不重传、不换名。minutes上传后分析失败也可能已经创建taskUuid，应按resume-id恢复；不把分析超时当“没有创建”。

固定版来源：[Drive事务实现](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/internal/helpers/drive.go)、[钉盘指南](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/blob/v1.0.67/skills/multi/dingtalk-drive/references/drive.md)。原始对象ID、签名地址和账号信息只留local，不进入IM报告或Git。

## 本人钉盘真实IM任务

veil原生私聊单次交办后，Kimi实际读宿主上下文和官方help、查询唯一mySpace与根目录，写唯一上传意图及57B UTF-8原件；官方drive +upload一次创建FILE，显式个人space-id/folder，无覆盖。随后按返回节点ID独立+info、+download，比较字节及SHA-256，保留所有操作回执。

liev完整短回复“原件与下载件字节一致，均为57字节”在客户端可见；57B TXT文件卡片原生下载至私有目录，Finder Quick Look实际打开，三行/中文/emoji正确。源文件、官方钉盘下载、outbox暂存和客户端下载件同字节，SHA-256为40b246d9478146acc659acf0a9afff40a642eb83934948206d2fe51ccf670347。远端合成件保留，不分享、不改权限、不删除。

scripts/accept_drive_ui.py只读39项通过；4个内存负向拒绝错误个人空间、错误下载节点、覆盖意图和篡改客户端下载字节。共享drive-ui-ledger.json、drive-audit-negative.json。1任务3确认，DM53/134（133确认1旧拒绝）/143/197，群3/7/12/76与旧记录日志不变；同native session，产品沿用E041，无部署变化。原观察1200样本10.001h、6不可达，历史3poll_error和维护保持，未满24h。

本结果是个人钉盘普通文件经真实IM交办的代表性闭环，不覆盖组织空间、权限、同步/覆盖/版本回滚，也未在veil账号内浏览liev钉盘。分钟听记创建/分析仍待验；下一独立项是预生成合成语音、本人上传听记、按taskUuid读取产物并通过IM下载打开报告，不录制环境或推送卡片，未知创建只对账。
