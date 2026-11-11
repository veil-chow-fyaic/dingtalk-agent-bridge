# 证据记录

2026-11-10 的 local-observations.json 为当前会话工具结果的脱敏结构化记录，AX 原始树不归档。upstream-metadata.json 是 GitHub 公开 issue 状态与最新正式版的元数据，不包含完整正文；故障范围以 docs 中链接和解释为准。

cli-baseline 保存本机真实版本和 Help；这些命令没有执行登录、订阅或发送。auth status 的独立检查可能具备刷新凭据行为；本次返回 authenticated=false，未出现授权流程。

后续每轮使用新日期或独立 run 目录，避免覆盖旧版本证据。只读采集命令：

```bash
python3 scripts/capture_local_baseline.py --output evidence/<日期>/<run>/cli-baseline
```

成功命令只证明该命令对应的检查项；参数帮助不能证明后端可用，UI 气泡不能证明对端已读。

new-org-onboarding.json 是同日后续记录，认证状态已更新为 true，当前目标改为新组织。早先 local-observations.json 保留开通前和旧群的历史，不覆盖。
