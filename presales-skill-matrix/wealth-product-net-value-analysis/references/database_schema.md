# 数据库结构定义

## 文件列表

| 文件 | 说明 | 更新频率 |
|------|------|---------|
| fund_companies.json | 基金公司基础信息 | 半年 |
| fund_managers.json | 基金经理完整档案 | 半年 |
| holdings_database.json | 持仓历史数据 | 季度 |
| style_profiles.json | 投资风格分类 | 半年 |

## fund_companies.json

```json
{
  "companies": [
    {
      "company_id": "C001",
      "name": "华夏基金",
      "short_name": "华夏",
      "type": "公募",
      "scale": 8000,
      "establish_date": "1998-04-09",
      "registered_capital": 2.38,
      "headquarters": "北京",
      "investment_style": {
        "overall_style": "综合型",
        "strength_areas": ["主动权益", "指数投资", "海外QDII"],
        "key_stocks": ["贵州茅台", "宁德时代", "招商银行"],
        "focus_sectors": ["消费", "科技", "金融"]
      },
      "manager_list": ["manager_id_1", "manager_id_2"],
      "philosophy": "价值投资、长期持有",
      "culture": "投研一体、团队协作",
      "rating": {
        "overall": 9,
        "research": 9,
        "performance": 8,
        "stability": 8
      },
      "last_updated": "2026-03-31"
    }
  ],
  "meta": {
    "total_count": 150,
    "last_update": "2026-03-31",
    "source": ["基金业协会", "天天基金网"]
  }
}
```

## fund_managers.json

```json
{
  "managers": [
    {
      "manager_id": "M001234",
      "name": "张明",
      "gender": "男",
      "birth_year": 1980,
      "education": "硕士",
      "company_id": "C001",
      "company_name": "华夏基金",
      "companies_history": [
        {"company": "易方达基金", "start": "2014", "end": "2018"},
        {"company": "华夏基金", "start": "2018", "end": "至今"}
      ],
      "fund_list": [
        {
          "fund_code": "000001",
          "fund_name": "华夏成长混合",
          "fund_type": "混合型",
          "incep_date": "2018-03-15",
          "scale": 50.5,
          "tenure_years": 5.2
        }
      ],
      "investment_style": {
        "type": "成长型",
        "sub_type": "积极成长",
        "market": "A股为主，港股配置10%",
        "sector": "科技、新能源",
        "position_style": "高仓位，鲜有择时",
        "turnover": "中等（年换手150%）",
        "concentration": "前十大55%"
      },
      "top_stocks": [
        {"code": "600519", "name": "贵州茅台", "weight": 5.2, "change": 0.3},
        {"code": "000858", "name": "五粮液", "weight": 4.8, "change": -0.5}
      ],
      "top_bonds": [],
      "fof_holdings": [],
      "tracked_index": null,
      "infrastructure_features": null,
      "investment_goal": "追求长期资本增值",
      "investment_scope": "股票仓位60-95%，港股通0-20%",
      "recent_views": [
        {"date": "2026-01-20", "content": "看好科技板块估值修复机会，关注AI应用端"},
        {"date": "2025-12-15", "content": "内需消费复苏是明年主线"}
      ],
      "performance": {
        "ytd": 5.2,
        "one_year": 18.5,
        "three_year": 45.2,
        "five_year": 89.3,
        "sharpe_ratio": 1.2,
        "max_drawdown": -22
      },
      "personality_traits": {
        "speech_style": "专业务实，逻辑清晰",
        "professional_level": 8,
        "human_touch": 7,
        "openness": 6,
        "stability": 8
      },
      "tags": ["科技", "新能源", "高仓位"],
      "last_updated": "2026-03-31"
    }
  ],
  "meta": {
    "total_count": 5000,
    "last_update": "2026-03-31",
    "source": ["天天基金网", "2025年报", "2026一季报"]
  }
}
```

## holdings_database.json

```json
{
  "holdings": [
    {
      "fund_code": "000001",
      "quarter": "2025Q4",
      "report_date": "2025-12-31",
      "stocks": [
        {"code": "600519", "name": "贵州茅台", "weight": 5.2, "shares": 120000},
        {"code": "000858", "name": "五粮液", "weight": 4.8, "shares": 800000}
      ],
      "bonds": [
        {"code": "019547", "name": "22国债01", "weight": 3.1, "face_value": 50000000}
      ],
      "funds": []
    }
  ],
  "meta": {
    "total_records": 50000,
    "last_update": "2026-03-31",
    "quarters": ["2024Q2", "2024Q4", "2025Q2", "2025Q4"]
  }
}
```

## style_profiles.json

```json
{
  "styles": [
    {
      "style_id": "S001",
      "name": "价值成长均衡型",
      "code": "VALUE_BALANCED",
      "description": "兼顾价值与成长，仓位适中，追求稳健收益",
      "characteristics": {
        "pe_range": [15, 30],
        "position_range": [70, 85],
        "turnover": "中等",
        "sector_distribution": "分散"
      },
      "suitable_investors": ["稳健型", "保守型"],
      "typical_managers": ["manager_id_1", "manager_id_2"]
    },
    {
      "style_id": "S002",
      "name": "积极成长型",
      "code": "AGGRESSIVE_GROWTH",
      "description": "高仓位高换手，专注成长赛道，追求超额收益",
      "characteristics": {
        "pe_range": [25, 50],
        "position_range": [85, 95],
        "turnover": "高",
        "sector_distribution": "集中"
      },
      "suitable_investors": ["积极型", "激进型"],
      "typical_managers": ["manager_id_3", "manager_id_4"]
    }
  ],
  "meta": {
    "total_styles": 12,
    "last_update": "2026-03-31"
  }
}
```

## 数据索引设计

为提高查询效率，建立以下索引：

```python
# 基金经理索引：按公司
manager_by_company = {
    "C001": ["M001", "M002", "M003"]
}

# 基金经理索引：按风格
manager_by_style = {
    "GROWTH": ["M001", "M003", "M005"],
    "VALUE": ["M002", "M004"]
}

# 基金公司索引：按规模
company_by_scale = [
    {"company_id": "C001", "scale": 8000},
    {"company_id": "C002", "scale": 7500}
]
```