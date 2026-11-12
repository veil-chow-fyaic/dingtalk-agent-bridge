# AIC 群媒体实测与结果契约修复

2026-11-12，E098真实UI、E099代码。范围只有AIC测试群，veil从原生客户端交办，DWS真人liev回复；没有创建bot或在企业大群发测试。原始任务、工具日志、客户端文件和UI诊断只在`local/aic-media-20261112/`。

## 用户实际看到和拿到的结果

| 项目 | 实际输入与执行 | UI交付和打开 |
|---|---|---|
| JPEG | 16061B/400×240原件；Kimi ReadMediaFile识别DAB-JPEG-029、VALUE=58和向右箭头，Pillow顺时针旋转90° | liev原生图片及独立查看器：箭头向下、240×400；客户端下载13834B，Finder Quick Look实际显示同图；SHA与产物一致 |
| WAV文件 | 32044B原件，Python wave真实读取：16kHz/单声道/16bit/16000帧/1秒/峰值1000 | 只读交付后群文件卡片下载；Finder Quick Look音频播放器显示1秒并到末尾；与输入及出站原件逐字节一致，不声称听觉质量 |
| MP4文件 | 1894B原件；ffprobe真实分析h264/320×180/1秒 | 群视频卡片打开，钉钉预览蓝色画面、00:01/00:01；客户端下载成功，Finder Quick Look实际显示同画面；SHA一致 |
| 分析报告 | 原AV任务产生439B UTF-8 TXT，记录两个原件SHA和分析结果 | 钉钉下载，TextEdit打开实际正文；SHA与原产物一致 |

JPEG保存框默认“图片.png”，将名称设为`aic-e098-rotated.jpg`后，钉钉仍追加`.png`。实际下载名为`aic-e098-rotated.jpg.png`，内容魔数及原SHA证明仍是JPEG，未改写或转换。保留此客户端命名差异。

[16项只读审计](../evidence/2026-11-12/aic-group-media-validation.json)核三任务、10个confirmed回执、三份入站原件、四份客户端下载件、实际工具及配置不变。审计不执行UI或DWS；上表UI由本轮电脑控制实际观察，不将脚本输出冒充用户可见证据。新增六格通过，矩阵47通过/16blocked/1partial；14 MUST仍8项不完整。原生语音条和独立video协议没有因此通过。

## 保留的失败及恢复

第一条图片消息实际含`1ye m/agent`前缀，桥接按普通内容接收、零任务。先核UI与原inbox/command_for，再发送精确`/agent`的新任务，未重放未知投递。JPEG仅一个任务，模型内部确实执行两次相同Pillow脚本并读图；不能把一个任务吹成工具只执行一次。

音视频原任务实际完成wave/ffprobe分析和三份产物，但Kimi最终消息在JSON前加说明文字，旧解析器报JSONDecodeError。原任务一直failed，只有接收和错误两个confirmed回执，未发送任何结果文件。随后从UI明确交办独立的只读核验/交付任务：一次Bash只算SHA，未重跑分析、未修改或重编码；三原产物交回，五回执confirmed。原failed没有改绿，文件也未替换。

用户操作钉钉期间出现管理员登录窗口，未点击授权。用户确认空闲后继续。CUA多次windowNotFoundAtPosition、一次无效截图尺寸和一次Quick Look捕获超时；按现态核对，没有据此重发任务。滚动/坐标两轮无进展后停止该路径，改用钉钉搜索＋方向键/回车跳到已有消息，成功取得旧文件。音频预览超时后重连实际看到了播放器才计通过。只读审计首轮误将配置名按仓库根解析，修正为local后16项通过，未更改现场配置。

## E099：通用结果失败契约

借鉴[CEO C03](references/ceo-deep-dive.md)的运行器终态/结果契约分离，用本项目接口实现，未复制新的上游代码。最终结果必须为恰含`text`字符串与`files`字符串数组的对象，最多10文件；LocalRuntime和gateway入口都校验，未来替换适配器不能跳过交付契约。

缺失、非法JSON、错误schema分别记录`runtime_result_missing`、`runtime_result_invalid_json`、`runtime_result_schema_invalid`，stage=result、retry_safe=false。保持整段JSON或完整JSON代码围栏兼容，拒绝前后解释文字、提示词回显、多对象、重复键、NaN/Infinity和额外字段。不能靠截取最后一个花括号把不确定结果强行当成功。

失败反馈明确告诉用户：结果格式无法确认、结果文件未交付、没有自动重做，工具可能已产生文件或其他变更，可先核验现有产物再单独交付。保留原工具日志、session、失败记录和部分产物，不自动重跑模型或业务；加强最终提示不等于保证模型永不输出错误格式。

新增8方法，包括真实合成Kimi进程、非Local适配器越界、失败后重启不重放、同session下一合法任务。冻结源码及同一wheel的Python3.14/3.11安装包各299通过、六入口/21模块一致、9项审计，见[验证](../evidence/2026-11-12/runtime-result-contract-validation.json)。当前代码已验证但本检查点尚未重载，真实E098使用部署E093；离线新错误提示不是新UI通过。

下一步在两gateway无运行/排队任务及未决投递时，通过现有Manager归属检查仅重载gateway，保留transport与账号配置；随后补群长文及status/cancel/new。不要重发以上三任务或再次下载已经验完的文件。
