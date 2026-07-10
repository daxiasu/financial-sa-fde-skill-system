# metric_mapping.md

## 常见问法映射

- 资产总计 -> total_assets
- 营业收入 -> revenue
- 净利润 -> net_profit
- 经营性现金流 -> operating_cashflow
- 授信余额 -> credit_balance
- 担保余额 -> guarantee_balance
- 逾期 -> overdue_flag / overdue_amount
- 关注类 -> concern_class_flag
- 应收账款异常 -> ar_ratio / ar_growth

## 时间口径规则

- 近四年 = T, T-1, T-2, T-3
- 最近三年 = 最近三个完整年度
- 截至本月 = 当前月末快照
- 按2008年为基准 = 以 2008 年为 T，回溯 T-1, T-2, T-3
