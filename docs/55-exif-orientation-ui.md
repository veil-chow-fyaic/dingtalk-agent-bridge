# EXIF方向JPEG的原件与真实处理

<!-- historical-scope:start -->
> **阶段历史，非当前操作指令。** 本文正文保持原阶段内容；“当前、下一步、待许可、暂停、未接入”均按本文实验时点解释。现状见[统一总览](102-user-requirements-and-roadmap.md)，操作见[运行手册](15-service-runbook.md)。旧失败及证据不因后续成功而删除，不照抄旧探针或恢复动作。
<!-- historical-scope:end -->


2026-11-12，E037。veil在原生钉钉私聊一次发送文字＋JPEG，Kimi实际检查EXIF、导出正向PNG，liev回传文字、原生图片和报告。完整短回复已在聊天中观察，两文件均从钉钉下载并用Finder Quick Look打开。

## 输入、工具与结果

合成fixture `fixtures/dab-exif-orientation6.jpg`只有Orientation=6这一项EXIF，无账号、位置或相机元数据。编码像素460×300；按方向显示为300×460，红色TOP条在上、绿色箭头向右，图内编号EXIF-037、数值73。提示要求检测，没有提供这些答案。

客户端草稿和已发送聊天按竖图正向显示（上、下两个视口分别观察）。DWS下载、bridge缓存、Kimi输入及ReadMediaFile实际收到的JPEG均与fixture字节完全一致，保留Orientation=6，没有在传输中转码或提前归正。未打开入站图片独立查看器，不把聊天截图命名误当查看器通过。

Kimi最初用Read读取图片被拒绝，随后Bash/Pillow读出编码尺寸和EXIF，ReadMediaFile读取原件；再实际调用ImageOps.exif_transpose，保存PNG并重新打开确认300×460、Orientation缺失，ReadMediaFile查看输出、Write生成462B报告。初始工具错误原样保留。

审计独立使用明确的顺时针90度像素变换，与runtime的EXIF处理调用分开：输出PNG逐像素精确相同，没有额外旋转。报告和完整短回复的尺寸、方向值、编号、数值均正确。钉钉查看器显示liev分享的图片、TOP在上/箭头向右；客户端下载PNG与export、bridge staged及两条官方资源别名同字节，报告与其官方资源同字节。

| 对象 | 字节 | SHA-256 |
|---|---:|---|
| JPEG原件 | 23810 | `948db8e1c5a27e05e72679cae51fb57bc9856c1307581dc176507a49e8976efe` |
| 正向PNG | 30666 | `6546be9d486a5fe1036da86f25545658570942f8c53ede9a29848f85f4efde17` |
| 报告TXT | 462 | `4db78d06970268c48ad45b3ed3dda6d4601c2477386e87b4178e246858d3b84d` |

## 复核与边界

`python3 scripts/accept_exif_ui.py`只读核验47项；`exif-audit-validation.json`四个负向场景均拒绝：同尺寸反向旋转、像素正确但残留Orientation=6、缺官方图片资源、短回复方向值错误。注入在内存和私有合成负向图片进行，不改真实账本/日志/下载件。

一条UI输入对应一个completed任务、四个confirmed回复（ack/text/image/file），没有自身回复循环。DM从46/114/123/170变为47/118/127/175；群3/7/12/76不变。旧任务/outbox/传输/运行日志与native session保持。无产品代码、配置、凭据或部署改动，E035的156回归/六入口18模块版本继续运行；不为纯证据增加重复回归。

本次只证明私聊的一个EXIF方向6样本。镜像方向2/4/5/7、其他方向、HEIC、动画、其他EXIF信息及群仍未覆盖。官方负责身份/消息/资源，既有image上传窄补充不变；归正由通用runtime执行，不添加格式专用传输后端。

UI工具曾在Finder关闭Quick Look并进入路径导航后超时；重绑定确认导航框已经打开后继续，未重复下载或发送。一次入站图片AX点击offscreen、一次只聚焦消息，均未被算作查看器成功。本地只读脚本最初命名inspect.py遮蔽标准库，改名后审计正常；不影响产品。

原始AX/截图/账本/下载/工具日志引用只在`local/exif-ui-20261112/`。04:24冻结原观察1056样本、8.800小时，累计6不可用；起点/run/PID保持，仍未满24h。
