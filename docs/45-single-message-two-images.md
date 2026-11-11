# 单消息双图片真实私聊验收

2026-11-12，E026。E026：veil原生私聊单条文字＋两PNG→一个Kimi任务、三确认回复；两次ReadMediaFile收到原件字节，Bash实际量尺寸/像素，420B报告客户端下载Quick Look打开，顺序为橙色矩形31、蓝色圆形46、合计77。38只读检查与3负向检查通过；两次初始Read图片错误保留。仅单消息双PNG通过，不外推任意多文件、出站多附件或群。当前DM40任务97outbox（96确认1拒绝）105传输146事件，群3/7/12/76保持。无产品/配置/部署变更，131回归版本保持；原观察799样本6.66h/5不可用，未满24h。

## 实际操作与结果

在原生钉钉veil→liev输入合成任务，Finder同时选择两个PNG，一次粘贴到同一草稿；确认文字后有两个图片对象，只点击发送一次。聊天中形成一条含两图片的输入，bridge的语义parts顺序为text、image、image，无别名合并或额外任务。

| 原件 | 内容 | 尺寸 | 字节 |
|---|---|---|---|
| dab-multi-image-a.png | DAB-MULTIIMG-A，31，橙色矩形 | 320×180 | 4330 |
| dab-multi-image-b.png | DAB-MULTIIMG-B，46，蓝色圆形 | 240×200 | 4753 |

提示仅要求按顺序提取编号、数值、颜色、形状、尺寸和求和，没有把答案提供给模型。模型先用Read读取图片，两次均被工具明确拒绝；随后分别用ReadMediaFile成功接收与原件相同的PNG字节，再以Bash/Python/Pillow测量尺寸和主要像素色。Write生成420B报告。

liev三条回复经同一路由确认。veil客户端文件卡片下载一次，在Finder Quick Look实际打开，报告全部结果与原件相符，SHA-256为bc51515c8cc73b7595b4e003b0ad5d112e53faccbaeaa46b7d86d8896a39f5e5。短文字回复没有单独UI补验；文件卡片、下载件和打开内容已验。旧任务、投递、日志及native session保持，自身回复不触发新任务。

## 复核与边界

只读命令：`python3 scripts/accept_multi_image_ui.py`。共享结论见[multi-image-ui-ledger.json](../evidence/2026-11-12/multi-image-ui-ledger.json)与[负向验证](../evidence/2026-11-12/multi-image-audit-validation.json)。内存中缺第二图、逆序、损坏下载三种变更均被拒绝；原始账本不改。

原始身份、截图、AX、运行日志和下载件只在local/multi-image-ui-20261112。共享fixtures只含合成数据。五张截图已逐张观察；草稿/发送两图及打开报告另有AX证据。

E017普通文件多选仍拆成两消息，本次没有改变该结论；本次只证明私聊一条消息两PNG。引用入站、群/出站单条多附件、原生语音条仍未通过。

引用入口另查官方客户端说明和原生设置：匿名气泡按钮未弹菜单；设置页两次快捷键导航仍停留通用页，已触发loop guard。未发送引用、未修改设置，不能声称官方没有快捷键。此路径原始观察在local/quote-shortcuts-20261112；下一步独立接入官方已存在的+messages-reply出站能力，引用入站保持未验。
