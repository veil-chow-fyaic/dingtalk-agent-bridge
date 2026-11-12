# E066：官方v1.0.68更新的只读边界核对

2026-11-12，针对E065中doctor的新版本提示，读取[官方v1.0.68发布页](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/releases/tag/v1.0.68)及[v1.0.67到v1.0.68比较](https://github.com/DingTalk-Real-AI/dingtalk-workspace-cli/compare/v1.0.67...v1.0.68)。正式版发布于2026-11-11 08:50:17 UTC，对应commit `ba02fc6cdbdb3543d21d0cdb70f027bf0d142692`；比较返回53个提交、218个变更文件。本段没有安装或执行新版，没有操作登录态。

| 与当前项目相关的内容 | 核对结果与行动边界 |
|---|---|
| macOS登录密钥读取 | 直接读取新版`internal/keychain/keychain_darwin.go`，与本地固定v1.0.67官方原件逐字节相同。公用keychain文件仅注释变化；发布中的存储隔离改动针对Windows。没有证据表明升级能修本机E065，不能用升级代替恢复现有访问。 |
| 本地图片上传补充 | 新版`internal/helpers/image_upload.go`与旧版逐字节相同；chat.go的67行diff没有新增上传叶子/注册。所检查的变更没有消除当前独立CHAT_IMAGE入口缺口，因此继续保留固定v1.0.67薄补充。此结论是源码差异核对，没有宣称已实测v1.0.68全部CLI。 |
| 聊天读完整性 | 发布及chat.go修改涉及解密错误归属、策略失败原因与分页可信度；升级评估时须核bridge对partial/解密失败的处理及旧事件投影，不能只测help就替换现场。 |
| 应用事件/卡片 | 新增应用事件定义命令与个人事件监听、bot身份不是同一能力；A2UI转发默认值改变不等于普通账号流式回复已经实现。当前授权仍不新建应用/bot或发布事件定义。 |

两份直接取得的官方源码SHA256及比较摘要见[脱敏证据](../evidence/2026-11-12/official-v68-boundary.json)；原始选取响应和源码留`local/dws-v68-review-20261112`。首个比较响应体很大，后续只提取相关字段/差异，避免反复输出整份官方源码。官方发布页中的其他功能不扩成已测试范围。

当前继续固定v1.0.67；新版本没有被用作故障绕行。E065恢复、未完成群UI及原24h观察仍是关键路径。本段既不新增UI通过，也不改变现有补充工具的上游固定commit。
