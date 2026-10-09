# 日本研究执行与审核安排

授权：用户2026-09-28要求按研究基线V2完成全部研究步骤后，一并提交review agent，模型指定astra high。

- 主线程承担研究与整合，文件位于countries/JP/research/；此处为研究工作区，不修改生产模型、代码或既有国家研究。
- 范围严格依照../japan_research_scope_draft_20260928.md；排除冲绳及离岛。
- JP-01至JP-10全部形成研究交付和问题清单后，统一提交独立只读审核，不逐模块调用审核。
- 最终审核用显式gpt-6-astra / high的通用Agent承担research_reviewer职责（当前预置research_reviewer仅medium，不能据角色名称声称high）。禁止子Agent再委派。
- 审核不得修改交付、状态或放行下一阶段。主线程修复可解决问题后，可提交同一审核Agent复核。
- 官方资料与研究时序原始文件在evidence/内按内容哈希保存，不覆盖；sources.jsonl记录获取时间、URL、SHA256及结果。
- 所有模块必须实质研究；证据或数据未闭合须明确列缺口，不能以完成章节替代完整范围通过。
- 允许历史基本面统计、作图和复现检查；不执行储能优化或收益回测。

当前：十模块交付已于2026-09-28整包提交 /root/japan_review；实际启动参数gpt-6-astra/high，初审及修订只读复核均为NOT_PASS。R01/R08修复关闭，其余未全部闭合，保持researching、modeling_approved=false。完整性缺口随包披露，不声称基线全部完成。
