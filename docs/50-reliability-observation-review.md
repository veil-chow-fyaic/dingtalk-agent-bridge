# 长期观察只读终检工具与阶段结果

2026-11-12，E031。新增 `scripts/review_service_observations.py`，只读已有捕获文件，区分记录完整性、是否达到24小时和是否记录过错误，不把仍在采集当成可靠性通过。

## 当前真实结果

原run仍是 `reliability-20261111`，11月11日19:36:08开始，未重置。冻结917样本、7.640小时、122个事件；样本最大间隔30.402秒。13项记录完整性检查通过，事件身份绑定原路由、序列递增、同路由消息ID无重复。群9＋私聊113个事件与同时段冻结SQLite原始事件逐行（含正文）相同；这只证明捕获与本地账本一致，不证明上游绝无漏消息。

记录保留6次服务不可达、3个poll_error样本（均私聊）、14条维护记录。三个轮询错误在01:01:24、01:01:54、01:02:24，对应E023受控history故障时段；没有因它们属于实验而删掉。不可达采样在22:52:17、23:17:18、23:17:48、01:09:54、01:26:25、02:25:59。采样不能覆盖两个采样点之间的短中断，维护与版本记录仍须单独审查。

`observation_complete_24h=false`、`zero_recorded_errors=false`。实际运行 `--require-complete` 返回退出码2，不能将本阶段结果标成24h通过或项目完成。

## 使用

```sh
python3 scripts/review_service_observations.py \
  --run-dir local/service-observations/reliability-20261111

python3 scripts/review_service_observations.py \
  --run-dir local/service-observations/reliability-20261111 \
  --require-complete
```

默认只打印脱敏聚合结果，`--output`显式写报告。退出码0表示记录完整性通过，1表示记录无效，2表示要求24h但未达；即使时长达标，也要另看错误、维护、代码版本，0不代表零故障稳定性验收。

当前原始冻结文件仅在 `local/reliability-review-20261112/`；复核该目录可得到相同摘要。读取活动目录若遇到样本写入与status替换的竞争，工具拒绝不一致，不偷偷修计数；应留待下一次完整采样或冻结一致快照。可选同目录 `ledger.json` 用于冻结本地账本对账，无该文件时不能声称完成账本核对。

时长门同时要求86400秒、active=false、stop_reason=duration_reached、实际末次采样靠近截止、连续采样无大缺口、wall/elapsed相符。允许尾窗为采样周期＋每路请求的8秒超时预算＋5秒；缺口预算为两个周期＋请求预算＋5秒。事件seq可能因INSERT OR IGNORE产生跳号，严格递增即可，不能拿跳号直接指认丢消息。

## 验证与范围

11个新增隔离测试覆盖实际24h边界、7.5小时活动样本、信号停止、缺失末尾、计数不符、采样缺口/时钟跳变、维护不抵消错误、重复/跨路由事件、账本同数量但正文篡改与缺项。真实917样本终检与退出码2均实际执行，输出未带账号/会话ID。

产品模块不变，E030的139项全量回归保持；本段只新增并运行11项观察工具测试，不宣称重新跑过150项全量。无新消息、配置或部署变更。共享结果：`evidence/2026-11-12/reliability-progress-review.json` 与 `reliability-review-validation.json`。最早11月12日19:36:08后再次评估时长，完整终检前心跳继续。
