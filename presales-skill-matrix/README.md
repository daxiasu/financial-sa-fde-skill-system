# 售前演示 Skill 矩阵

本目录用于沉淀金融行业售前演示型 Skill。

目标不是直接承载客户真实生产数据，而是用模拟数据、脱敏场景和可解释工作流，展示 AI Skill 如何进入金融业务流程。

## Skill 矩阵规划

| 编号 | Skill 名称 | 方向 | 状态 | 路径 |
|---|---|---|---|---|
| G0 | 授信走访前穿透式风险分析 | 银行对公信贷/风控 | 已完成首版 Demo | `ground-zero-credit-risk-analysis/` |
| G1 | 贷后风险监测报告生成 | 银行对公贷后/风控 | 已完成首版 L1 调用链路 Demo | `post-loan-risk-monitoring/` |
| G2 | 上市公司公告解读 | 投研/风控/公开信息分析 | 待规划 |  |
| G3 | 金融客户 KYC 画像生成 | 营销/财富/客户经营 | 待规划 |  |
| G4 | 金融政策解读与影响分析 | 合规/政策/经营管理 | 待规划 |  |
| G5 | 理赔材料智能分类与审核 | 保险/运营 | 待规划 |  |

## Ground Zero

`ground-zero-credit-risk-analysis/` 是本矩阵的第一个技能样板。

它用于验证一套完整链路：

```text
业务场景选择
  ↓
Skill 设计
  ↓
业务规则定标
  ↓
模拟数据集
  ↓
本地可视化 Demo
  ↓
GitHub Pages 发布
  ↓
版本化更新
```

## 每个演示 Skill 建议包含

```text
skill-name/
├── SKILL.md
├── references/
│   ├── risk_rules.md 或 business_rules.md
│   ├── report_template.md
│   └── test_cases.md
├── data/
│   └── simulated_dataset.json
├── scripts/
│   └── smoke_test.py
├── demo.html
└── demo_outputs/
```

## 售前演示边界

- 不使用真实客户数据。
- 不使用客户私有接口。
- 不展示客户内部规则。
- 不输出正式审批、定价、评级或合规结论。
- 所有演示结论必须标明“模拟数据”和“人工复核”边界。
