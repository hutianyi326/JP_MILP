# 日本研究第四轮独立审核与主线程验收

日期：2026-09-29 JST。审核员：/root/japan_review_round3，实际 gpt-6-astra / high；只读、无下级委派。

## 独立结论

**PASS；未关闭 P0=0、P1=0、P2=0。** 同意进入带输入门禁的MILP Markdown数学说明；不批准生产代码、真实项目收益回测或未核历史规则执行。最终对象为 review_round4_submission_v2.json，17/17 SHA匹配且结束时无变化。此前第三轮NOT_PASS及第四轮首送清单原样保留。

|第三轮问题|结论|证据与修复|
|---|---|---|
|P1/R06 容量版本与返金|关闭|capacity_closure_round3.md取消交付年度机械套版，2020版仅文献；K25 PDF pp2/5/27–28/37；2026以后相关退出受供给可靠度例外，Z是公开年度参数；混用两类过渡系数的概述已删|
|P1/R05 无合同计量/旧低压|关闭|history_closure_round3.md及history_settlement_revision_20260928.md同步；E03 pp98–99/678、E02 pp60–65；仅B/C无合同整地点G=0/D=A，A无合同禁用待确认；低压不套高压Tr1/Tr2|
|P2/R04 生效期|关闭|S1–S3旧链与2026-03-14起S4机器点/IoT/低压链分开；E36/E37/E38/E34已归档|

## 独立检查

336非空官方源SHA全匹配；17项冻结文件全匹配；无合同零流105 kWh、普通分支112 kWh复算一致；罚则500000 JPY、通常返金300000 JPY、例外返金0正确。第三轮的126ZIP成员、44226原始数值抽样、54原生网格、11704离线块及区域统计结论保持，相关数据未变。主线程31项检查PASS；审核未运行写文件验证、MILP或收益回测。全包回归未发现新增实质冲突，R01—R12当前关闭。

## 保留限制与主线程验收

主线程接受该独立结论，研究状态research_confirmed；modeling_approved=true仅限用户要求的数学MD；implementation_approved=false、historical_backtest_approved=false。

- 九区不含冲绳及离岛。不可拆分基本面和府县装机代理继续DIAGNOSTIC，禁止合规总量和模型输入，符合V2允许登记覆盖缺口。
- 未核JEPX历史条款/费率、历史容量和网络费用版本禁用；J19–21是补充/发现材料，失败响应非证据。
- 实测激活、历史决策可见版本、并网/BG/聚合合同、预认证、工程参数仍待输入，不能默认零。
- 2 MW/8 MWh不是低压证明；低压按合格资源聚合总量建模；单点资格待确认。一般特別高圧与部分22 kV例外、设备容量与投标量分开。
- 东北基准、东京/九州对照仅研究案例选择，非投资收益排名。
- 下一交付必须描述参与方式、历史/现行报价顺序、输入、变量、目标函数、物理与市场约束，规则/解释/假设分层，完成后同一Astra high独立审核至PASS。

官方核心来源：

- [OCCTO 2025年7月容量確保契約約款](https://www.occto.or.jp/assets/market-board/market/jitsujukyukanren/files/250731_kakuhokeiyaku.pdf)，PDF pp2、5、27–28、37。
- [EPRX第10版指南](https://www.eprx.or.jp/outline/docs/guide_ver.10_260701.pdf)，PDF pp98–99、678。
- [EPRX v18規程](https://www.eprx.or.jp/outline/docs/kitei_ver.18_260701.pdf)，PDF pp60–65。

完整逐项来源、日期、访问日期及其他机构资料见evidence_register.md及各专题附件；本验收不改写历史审核记录。
