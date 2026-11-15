# OpenClaw 本地薄适配 E127

2026-11-15：增加可选 `openclaw` 本地执行器，复用既有 gateway、任务、workspace、text/files、outbox 和自有进程 guard。固定官方 `41f2b981` 的完整 CLI 加回环合成 provider 已验证适配链路；尚未验证真实模型或钉钉 UI，未迁移现有会话或部署本轮代码。AIC Kimi、原私聊 Pi 的最近真实部署仍是 E123/e7d82cc。

## 命令与唯一宿主

使用 `agent --local --agent main --session-id <完整UUID> --json --timeout <整数秒> --message-file -`，不使用远端 Gateway、每次新 UUID 的 `agent exec` 或原生 `--deliver`。UUID 在启动工具前记入原任务账本；CLI 非零退出、取消或未输出完整 JSON 也不会遗失本轮所用 session。任务不自动重放，旧失败与副作用不确定性保留。

输出按完整 JSON 对象解析，只有 exit 0、UUID 一致、meta.stopReason/completion.stopReason 为 stop、明确 aborted=false、无 error/timeout、无工具失败或 unresolvedError 才从 `finalAssistantVisibleText` 解通用结果。payload、工具输出或提示词不能替代最终 assistant。length 即使 exit 0 也拒绝交付；拒绝重复键、非有限数、多对象和夹杂说明。

**replayInvalid=true 不是失败判据。** 官方工具完成代码在产生副作用时设置此字段；成功 Python 写文件同样如此。首版适配曾误拒绝，修正后允许交付满足上述终态的结果，但不允许自动重放。原失败、实际生成的文件、修正前后测试均保留。这是本轮完整入口联调发现的产品错误，不能用首版 419 项全绿掩盖。

取消和宿主期限沿既有 lifetime pipe，先向自有 CLI 发原生 SIGINT，让其取消内部工具，再有界清理其进程组。guard 的 5 秒原生等待、5 秒组终止及宿主最多 15 秒清理不扩大生产请求期限；不触碰共享 DWS bus。清理保证不外推恶意脱组程序或系统失效。

## 专用配置与绑定

[配置模板](examples/openclaw-host.example.json) 仅展示已核的最小宿主形状，不能直接连接真实服务。runtime 示例：

```json
{
  "kind": "openclaw",
  "binary": "/absolute/path/to/operator-managed-openclaw",
  "model": "fixture/model",
  "timeoutSeconds": 90,
  "openclaw": {
    "configPath": "/absolute/path/to/private/dedicated-host-v1.json",
    "configSha256": "<SHA256 of the exact dedicated config bytes>"
  }
}
```

配置必须是工作区之外的独立 JSON 文件。当前只接受单个明确的 OpenAI-completions provider/模型、内建 OpenClaw runtime、main agent、exec/process 工具；关闭插件、技能自动发现、shell 环境导入和业务通道。模板中的三处 `${DAB_OPENCLAW_WORKSPACE}` 必须保留，由适配器传入当前 generation 的工作目录，不能只依赖进程 cwd。拒绝其他 agent/ACP、路径覆盖、任意环境替换和任意层级 `$include`。文件摘要在构造及每个 turn 前核验；bridge 只引用配置，不复制凭据或合并默认账户配置。

home/state/cache/tmp 均放在本代工作区 `.openclaw-host/`，profile 根据该工作区路径派生；遇到逃逸符号链接或系统 HOME 下同名 profile 已存在时拒绝。子进程只继承 PATH、locale、时区与显式网络环境，去除环境中的 provider key、NODE_OPTIONS、shell hook 和默认 OpenClaw 配置变量，不覆盖 HOME/CODEX_HOME。原生配置设为只读。

配置路径、摘要及 agent 进入绑定与 session 契约；其他三种 runtime 的原绑定字节不变。更换 OpenClaw 配置应保留原不可变版本、使用新版本路径，先原生 new、零未决、停 gateway，再执行既有显式迁移工具。改 JSON 或摘要不能绕过原会话。迁移脚本只改绑定和审计行，保留所有旧任务/outbox，不启动服务。真实凭据配置、认证或迁移不属于本轮已执行动作。

这些是宿主选择与环境边界，**不是 OS 沙箱**。E126 已证官方仍可能作 login-shell PATH 探测及系统 HOME 的 App token 存在性探测；本轮合成验证继续使用读/启动保护，只放行从未存在的派生 profile token 路径，文件若出现即拒绝读取。不能外推任意生产配置或普通 binary 已完全杜绝环境访问。图片能力未声明；真实 provider、安装入口和安全 Node 补丁需另行验收，不能直接把 local 构建的测试 wrapper 作为生产安装。

## 验证与保留失败

[脱敏证据](../evidence/2026-11-15/openclaw-adapter-validation.json) 记录各冻结版本，完整原始材料仅在 `local/openclaw-adapter-20261115/`。

- 首次新增单测 18 项中 2 个测试路径断言错误：macOS `/var` 与 `/private/var` 别名。校正 fixture 的真实路径后通过，不放宽产品路径检查。
- 首次联调因 `Projects/projects` 路径拼写与官方构建 worker 的绝对路径不同，读保护拒绝源码 worker，未到 provider；校正验证工具工作目录拼写，原拒绝保留。未执行 CLI 提示的 doctor。
- 首版冻结源码/同 wheel 双 Python 各 419 通过，但随后完整 CLI 的成功工具触发上述 replayInvalid 误判；三套旧绿只说明旧覆盖，不是最终正确性。
- 修正后的 6 个完整 CLI 样本、18 检查通过：首次、同 UUID 续接、实际 Python `31*17+8=535` 并写 `exports/value.json`、相同 UUID 在新 generation 无旧历史、length 拒绝、取消。取消发生在 10 秒工具睡眠开始后，工具 PID 退出，观察至起点后至少 12 秒无晚写，guard 记录原生中断成功，取消/length 均无 validated-response。
- 上述 6 样本属于递归 include 拒绝加固前的固定产品。后续仅收紧配置验证（嵌套 include、缺明确 endpoint），追加配置负例和显式迁移两方法；不把旧 CLI 运行改称最终新版本，也不重复整套样本。另只读核对已捕获 5 份完整 JSON 的 systemPromptReport.workspaceDir，均对应实际 generation；取消无完整 JSON，不算第 6 份工作目录回读。

最终 22 个新增方法，冻结源码与同 wheel 的 Python 3.14.6 / 3.11.15 各 423 项通过；22 产品模块、177 份测试/工具/素材、六入口和许可字节一致。加固前另一冻结版本的 420×3 也通过，和首版 419×3 分开保留。最终配置接受同一已成功合成配置，AST/字节复核确认只有 validate_host_config 收紧，其余命令、环境、终态解析及产品模块未改；未重复完整 CLI 样本。详细冻结结果见证据 JSON。许可、六入口、全部产品模块和测试素材均按该冻结源与同一 wheel 比对；不把旧 E122/E124 运行算成新的全量。

补充固定依据：[配置环境替换及副作用重放语义](references/openclaw-adapter-contract.json)，沿 E126 的 36 文件再核 4 文件；未运行上游全量测试、未发布 issue/PR。原观察/Qwen/已过 UI 不重复，49/14/1 与 7 个 MUST 缺口保持，四 runtime 全过不是新增门槛。下一步是最终配置边界复核与必要的宿主异常退出覆盖；真实 OpenClaw 配置与 UI 未验不能冒充完成。


E128后续：[父进程死亡、两次恢复不重做与gateway原生new](129-openclaw-gateway-lifecycle.md)已补证，25官方CLI合成检查、3新增专项三环境通过；本页E127各版本/失败边界保持，产品未改或部署。
