# 安装包与只读 doctor

2026-11-11。项目现在可以安装为 `dingtalk-agent-bridge==0.1.0`，提供五个入口：`dab`（HTTP工具）、`dab-bridge`（传输）、`dab-agent`（可选本地执行器）、`dab-consume`（持久消费）、`dab-doctor`（只读诊断）。传输和通用工具不依赖 Kimi/Codex。

## 安装与工作目录

在已有项目检出中安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/dab-doctor --help
```

运行时只有Python标准库；构建使用PyPI的setuptools。要求Python≥3.11和POSIX（使用fcntl）；本轮实际测试的是macOS arm64/Python3.14.6，其他Python版本与Linux尚未实机认证，Windows不能由wheel名称推断支持。DWS及图片上传补充不捆绑进包，分别按官方固定版本与[图片补充构建说明](../integrations/dws_image_upload/README.md)配置。

服务、gateway、consumer以启动时工作目录为数据根。安装后的 `dab` 默认同样从当前目录读取 `local/runtime/http-token`，已修复原先会找进site-packages目录的问题；需要从其他位置调用时显式传 `--token-file`。不要复制别人的local目录作配置。

首次配置从公共 `config.routes.example.json` 与 `config.agent.example.json` 开始，填自己已验证的profile、会话ID、selfSenderId和执行人白名单。占位符不是可运行配置。鉴权/身份发现及组织边界见[开通手册](11-onboarding-lessons.md)与[通用接入](22-generic-tool-and-consumer.md)。没有任何安装步骤自动新建bot、邀请成员或扩权限。

配置后从同一工作目录前台运行：

```bash
.venv/bin/dab-doctor --config local/service-config.json
.venv/bin/dab-bridge --config local/service-config.json
# 另一个终端；只读本机健康检查
.venv/bin/dab-doctor --live
# 仅在明确配置了允许执行人后启动；该命令会实际承接任务并回复
.venv/bin/dab-agent --config local/agent-config.json
```

当前客户端/gateway/consumer默认连接127.0.0.1:18768。后台控制仍是检出目录内的service_ctl.py/agent_ctl.py，管理选中的单进程；统一多worker启动/停止尚未交付。安装包验证不意味着开机自启、后台管理和全部产品验收完成。

## doctor语义

```bash
python3 -m dingtalk_bridge.doctor   --agent-config local/agent-config.json   --agent-config local/agent-direct-config.json --live
```

默认离线，只读配置/文件和已有SQLite，不实例化会写状态的Bridge/Gateway，也不创建缺失账本。诊断包括显式身份与路由、DWS可执行文件、imageUploadBinary构建摘要、传输scope、未知投递数量、每个可选gateway的白名单/执行器/历史runtime binding、保留失败任务、HTTP token权限。

`--live`只增加携带本机token的loopback `/v1/health` GET：核对实际路由集合、最近完整同步（默认90秒）和poll_error。禁用环境代理和HTTP重定向，避免把本机token转交其他地址。输出只用route-1/agent-1序号及统计，不打印profile、账号/会话ID、令牌、聊天或服务端错误正文。

退出0表示这次检查无error，仍可能有warning；退出1表示存在错误。未初始化状态、未配置可选图片上传、历史失败均明确区分。现场结果为31项检查、1个warning：那条已有PNG别名历史blocked任务继续保留，不删记录变绿。doctor不发送探针、不重试任务、不续授权、不启动/停止进程；也不证明运行进程已经加载当前代码、模型真的可调用、UI投递成功或24h稳定。

## 实际安装与回归证据

从Git暂存树导出全部跟踪文件到隔离目录，不含local账号状态；在新venv构建wheel并安装。五个已安装入口在空工作目录均通过--help；缺配置doctor明确退出1且不创建状态；确认import来自venv的site-packages；wheel仅含Python包和发行元数据，所有模块摘要与最终源码相同。安装后的doctor显式指向当前已授权项目，实际检查两条活跃路由；未复制账号文件。

9项新增诊断/安装路径测试覆盖：离线不调用网络/不创建状态、占位符/缺配置、同步过期/不完整/路由错误、账本身份冲突不修复、白名单/runtime冲突、构建摘要/令牌权限、401脱敏、重定向不带token跟随、CLI从工作目录读token；账本读取显式关闭连接。全量93项在干净导出中通过。构建与测试原始日志留local，脱敏证据见[安装验证](../evidence/2026-11-11/clean-install-validation.json)、[现场doctor](../evidence/2026-11-11/doctor-live.json)、[回归](../evidence/2026-11-11/scenario-regression.json)。

本轮还尝试从原生UI引用既有报告，消息菜单受CUA窗口坐标定位错误阻塞，未发出新消息；没有把普通文本替代成“引用通过”。窗口已恢复原显示器。该项与包安装是独立证据，后续继续补引用/多附件、状态/取消、统一管理和恢复。
