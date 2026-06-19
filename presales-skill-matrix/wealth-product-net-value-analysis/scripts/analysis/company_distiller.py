"""
基金公司信息蒸馏脚本
对基金公司进行画像、特征提取、话术生成
"""
import json
import os
import random
from datetime import datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class CompanyDistiller:
    """基金公司蒸馏器"""

    def __init__(self):
        self.company_slogans = [
            "专注价值，稳健前行",
            "长期主义，价值投资",
            "精选个股，深度研究",
            "以客户为中心，以回报为目标",
            "专业创造价值，持有创造财富",
        ]

        self.culture_templates = {
            '大型': [
                "我们投研团队规模超百人，覆盖多个研究领域，强调团队协作和资源共享。",
                "强大投研平台支撑，资源共享，信息透明，让投资决策更科学。",
            ],
            '中型': [
                "投研团队精干高效，反应迅速，注重深度研究而非广撒网。",
                "我们坚持小而精的路线，每个研究员都是各自领域的专家。",
            ],
            '小型': [
                "灵活高效的投研机制，敢于逆势布局，捕捉边缘机会。",
                "小团队大视野，我们更专注于特色领域的深度研究。",
            ],
        }

        self.strength_keywords = {
            '科技': ['易方达', '华夏', '广发', '嘉实', '富国', '博时'],
            '新能源': ['农银汇理', '平安', '鹏华', '泓德'],
            '消费': ['汇添富', '景顺长城', '华安', '中欧'],
            '医药': ['融通', '长城', '银河', '国泰'],
            '价值': ['东方红', '兴全', '交银', '工银瑞信'],
            '成长': ['中邮创业', '银河', '浙商', '财通'],
        }

    def load_data(self):
        """加载数据"""
        with open(f'{DATA_DIR}/fund_companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
        with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
            managers_data = json.load(f)

        # 加载AUM数据
        aum_data = {}
        aum_file = f'{DATA_DIR}/company_aum_raw.json'
        if os.path.exists(aum_file):
            with open(aum_file, 'r', encoding='utf-8') as f:
                import pandas as pd
                df = pd.read_json(f)
                for _, row in df.iterrows():
                    aum_data[row['基金公司']] = {
                        'scale': row['全部管理规模'],
                        'fund_count': row['全部基金数'],
                        'manager_count': row['全部经理数'],
                        'founded': row['成立时间']
                    }

        return companies.get('companies', companies), managers_data.get('managers', []), aum_data

    def distill_all_companies(self):
        """蒸馏所有公司"""
        print("开始蒸馏基金公司信息...")

        companies, managers, aum_data = self.load_data()
        print(f"公司数: {len(companies)}, 经理数: {len(managers)}, AUM数据: {len(aum_data)}")

        # 按公司分组经理
        managers_by_company = {}
        for m in managers:
            company = m.get('company_name', '')
            if company not in managers_by_company:
                managers_by_company[company] = []
            managers_by_company[company].append(m)

        # 统计公司规模分类（使用AUM数据）
        scale_data = {}
        for c in companies:
            company_name = c['name']
            # 尝试匹配AUM数据
            scale = 0
            for aum_name, aum_info in aum_data.items():
                if aum_name.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '') in company_name or company_name in aum_name:
                    scale = aum_info['scale']
                    break
            if scale == 0:
                scale = c.get('total_scale', 0)

            if scale > 5000:
                scale_data[company_name] = '大型'
            elif scale > 1000:
                scale_data[company_name] = '中型'
            else:
                scale_data[company_name] = '小型'

        # 蒸馏每个公司
        distilled = []
        for c in companies:
            company_name = c['name']
            company_managers = managers_by_company.get(company_name, [])
            aum_info = {}
            for aum_name, info in aum_data.items():
                if company_name in aum_name or aum_name.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '') in company_name:
                    aum_info = info
                    break

            distilled_company = self.distill_company(c, company_managers, scale_data.get(company_name, '小型'), aum_info)
            distilled.append(distilled_company)

            if len(distilled) % 20 == 0:
                print(f"进度: {len(distilled)}/{len(companies)}")

        # 保存
        output = {
            'companies': distilled,
            'meta': {
                'total': len(distilled),
                'last_update': datetime.now().strftime('%Y-%m-%d'),
                'source': '天天基金网 + 基金业协会'
            }
        }

        with open(f'{DATA_DIR}/fund_companies.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"蒸馏完成! 公司数: {len(distilled)}")
        return distilled

    def distill_company(self, company, managers, size_category, aum_info=None):
        """蒸馏单个公司"""
        if aum_info is None:
            aum_info = {}

        scale = aum_info.get('scale', company.get('total_scale', 0))

        c = {
            'company_id': company.get('company_id', ''),
            'name': company.get('name', ''),
            'short_name': self._extract_short_name(company.get('name', '')),
            'type': company.get('type', '公募'),
            'total_scale': scale if scale else company.get('total_scale', 0),
            'total_funds': aum_info.get('fund_count', company.get('total_funds', len(managers))),
            'manager_count': aum_info.get('manager_count', len(managers)),
            'scale_category': size_category,
            'founded_date': aum_info.get('founded', company.get('founded_date', '')),
            'last_updated': datetime.now().strftime('%Y-%m-%d')
        }

        # 经理风格分布
        style_dist = Counter(m.get('investment_style', '均衡型') for m in managers)
        c['style_distribution'] = dict(style_dist)

        # 主导风格
        dominant_style = style_dist.most_common(1)[0][0] if style_dist else '均衡型'
        c['dominant_style'] = dominant_style

        # 平均任期
        tenures = [m.get('tenure_days', 0) for m in managers if m.get('tenure_days', 0) > 0]
        c['avg_tenure_days'] = sum(tenures) / len(tenures) if tenures else 0

        # 有持仓的经理比例
        has_holdings = sum(1 for m in managers if m.get('top_stocks'))
        c['holdings_coverage'] = round(has_holdings / len(managers) * 100, 1) if managers else 0

        # 行业分布（基于持仓）
        sector_count = Counter()
        for m in managers:
            for s in m.get('top_stocks', []):
                sector = self._detect_sector(s.get('stock_name', ''))
                if sector:
                    sector_count[sector] += 1

        if sector_count:
            c['sector_focus'] = [s for s, _ in sector_count.most_common(5)]
        else:
            c['sector_focus'] = []

        # 公司介绍
        c['company_intro'] = self._generate_company_intro(c, managers, size_category)

        # 投资理念
        c['investment_philosophy'] = self._generate_philosophy(c, dominant_style)

        # 投研文化
        c['culture'] = self._generate_culture(c, size_category)

        # 公司slogan
        c['slogan'] = random.choice(self.company_slogans)

        # 推荐理由
        c['recommendation'] = self._generate_recommendation(c)

        # 旗下明星经理（选择任期长、规模大的）
        stars = []
        for m in managers:
            if m.get('tenure_days', 0) > 365 * 3 and m.get('top_stocks'):
                stars.append({
                    'manager_id': m.get('manager_id'),
                    'name': m.get('name'),
                    'style': m.get('investment_style'),
                    'tenure_years': round(m.get('tenure_days', 0) / 365, 1),
                    'fund_name': m.get('current_fund_name', ''),
                    'personality_intro': m.get('personality_intro', '')[:100]
                })
        c['star_managers'] = stars[:5]  # 最多5个明星经理

        return c

    def _extract_short_name(self, full_name):
        """提取简称"""
        # 去除"基金管理有限公司"等后缀
        suffixes = ['基金管理有限公司', '基金有限公司', '有限公司', '股份有限公司']
        name = full_name
        for suf in suffixes:
            if name.endswith(suf):
                name = name[:-len(suf)]
        return name

    def _detect_sector(self, stock_name):
        """判断股票行业"""
        sector_keywords = {
            '科技': ['科技', '软', '硬', '电子', '通信', '计算机', '半导体', '芯片', 'AI', '人工智能'],
            '新能源': ['新能源', '光伏', '锂', '电池', '储能', '电动车', '汽车', '动力'],
            '消费': ['酒', '消费', '食品', '饮料', '家电', '商贸', '旅游', '酒店'],
            '医药': ['医药', '医疗', '生物', '疫苗', '中药', '健康'],
            '金融': ['银行', '保险', '券商', '信托', '地产', '物业'],
            '制造': ['机械', '化工', '材料', '军工', '航空', '制造', '设备'],
        }
        for sector, keywords in sector_keywords.items():
            if any(kw in stock_name for kw in keywords):
                return sector
        return None

    def _generate_company_intro(self, company, managers, size_category):
        """生成公司介绍"""
        lines = []
        name = company.get('short_name', company['name'])

        lines.append(f"{name}是国内知名的公募基金管理公司。")

        scale = company.get('total_scale', 0)
        if scale > 0:
            scale_str = f"{scale:.0f}亿元"
            lines.append(f"管理总规模超过{scale_str}，服务投资者数以百万计。")

        manager_count = company.get('manager_count', 0)
        if manager_count > 0:
            lines.append(f"拥有{manager_count}位专业基金经理，涵盖成长、价值、均衡等多种投资风格。")

        dominant = company.get('dominant_style', '均衡型')
        if dominant == '成长型':
            lines.append("在成长投资领域有深厚积累，重点布局科技、新能源等高景气赛道。")
        elif dominant == '价值型':
            lines.append("坚持价值投资理念，注重估值安全边际，追求稳健回报。")
        else:
            lines.append("采用均衡配置策略，兼顾收益与风险，追求长期稳健增值。")

        return '\n'.join(lines)

    def _generate_philosophy(self, company, dominant_style):
        """生成投资理念"""
        philosophies = {
            '成长型': [
                "我们相信优秀的企业能够穿越周期，通过深度研究挖掘高成长标的，分享企业价值增值的成果。",
                "成长投资是我们的核心能力圈，通过产业链研究和技术趋势判断，把握科技、新能源等领域的投资机会。",
            ],
            '价值型': [
                "我们坚持又好又便宜的投资原则，通过估值分析寻找安全边际，追求风险调整后的最优回报。",
                "价值投资是一场马拉松，我们注重长期收益，不追求短期排名，致力于为投资者创造可持续的回报。",
            ],
            '均衡型': [
                "我们相信资产配置的力量，通过行业分散和风格平衡，控制回撤的同时捕捉市场机会。",
                "投资如做人，讲究均衡之道。我们追求攻守兼备的组合，在不同市场环境下都能稳步前行。",
            ],
        }
        return random.choice(philosophies.get(dominant_style, philosophies['均衡型']))

    def _generate_culture(self, company, size_category):
        """生成投研文化"""
        cultures = self.culture_templates.get(size_category, self.culture_templates['中型'])
        culture = random.choice(cultures)

        tenure = company.get('avg_tenure_days', 0)
        tenure_years = tenure / 365 if tenure > 0 else 0

        if tenure_years > 1500:  # 平均4年以上
            culture += f"核心投研团队平均从业年限超过{int(tenure_years/365)}年，经验丰富，稳定可靠。"
        elif tenure_years > 1095:  # 3年以上
            culture += "团队注重梯队建设，新老结合，保持投研活力的同时传承经验。"

        return culture

    def _generate_recommendation(self, company):
        """生成推荐理由"""
        name = company.get('short_name', company['name'])
        scale = company.get('total_scale', 0)
        dominant = company.get('dominant_style', '均衡型')
        sectors = company.get('sector_focus', [])

        reasons = []

        if scale > 10000:
            reasons.append(f"{name}是行业头部公司，管理规模超万亿，实力雄厚，平台优势明显。")
        elif scale > 5000:
            reasons.append(f"{name}管理规模超五千亿，位列行业第一梯队，综合实力强劲。")
        else:
            reasons.append(f"{name}是业内知名公司，有自己的特色投研优势。")

        if dominant == '成长型':
            reasons.append("成长风格突出，适合看好科技、新能源等高景气赛道的投资者。")
        elif dominant == '价值型':
            reasons.append("价值风格稳健，适合追求稳健收益、控制回撤的投资者。")
        else:
            reasons.append("风格均衡稳健，适合希望均衡配置、分散风险的投资者。")

        if sectors:
            sector_str = '、'.join(sectors[:3])
            reasons.append(f"公司在{sector_str}等领域有较强的投研能力。")

        return ' '.join(reasons)


def main():
    distiller = CompanyDistiller()

    print("=" * 60)
    print("基金公司信息蒸馏")
    print("=" * 60)

    distilled = distiller.distill_all_companies()

    # 展示示例
    print("\n示例 - 华夏基金:")
    for c in distilled:
        if '华夏' in c['name']:
            print(f"  简称: {c.get('short_name')}")
            print(f"  规模: {c.get('total_scale', 0):.0f}亿元")
            print(f"  主导风格: {c.get('dominant_style')}")
            print(f"  风格分布: {c.get('style_distribution')}")
            print(f"  行业聚焦: {c.get('sector_focus')}")
            intro_lines = c.get('company_intro', '').split('\n')
            intro_text = '\n    '.join(intro_lines)
            print(f"  公司介绍:\n    {intro_text}")
            print(f"  投资理念: {c.get('investment_philosophy')}")
            print(f"  推荐理由: {c.get('recommendation')}")
            if c.get('star_managers'):
                print(f"  明星经理: {[m['name'] for m in c['star_managers'][:3]]}")
            break

    print("\n" + "=" * 60)
    print("蒸馏完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()