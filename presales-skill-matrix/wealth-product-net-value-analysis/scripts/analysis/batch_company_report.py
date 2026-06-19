"""
批量生成所有基金公司的完整分析报告
"""
import json
import os
from datetime import datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class CompanyReportGenerator:
    """公司报告生成器"""

    def __init__(self):
        self.stage_templates = {
            '萌芽期': "基金成立不久，正处于建仓期运作，需要一定时间验证投资策略的有效性。",
            '成长期': "基金已经度过建仓期，开始展现出一定的投资特色，业绩弹性较大。",
            '成熟期': "基金运作成熟，风格稳定，业绩归因清晰，是配置的好选择。",
            '老牌期': "老牌基金，经历过多次市场周期，风格非常稳定。",
        }

    def load_data(self):
        """加载数据"""
        with open(f'{DATA_DIR}/fund_companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
        with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
            managers_raw = json.load(f)
        managers = managers_raw.get('managers', managers_raw)
        return companies.get('companies', companies), managers

    def detect_sector(self, stock_name):
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

    def analyze_manager(self, m, company_name):
        """分析单个经理"""
        top_stocks = m.get('top_stocks', [])
        tenure = m.get('tenure_days', 0)

        # 行业分布
        sectors = []
        for s in top_stocks:
            sec = self.detect_sector(s.get('stock_name', ''))
            if sec:
                sectors.append(sec)
        sector_count = Counter(sectors)
        main_sectors = [s for s, _ in sector_count.most_common(3)]

        # 确定阶段
        if tenure < 180:
            stage = '萌芽期'
        elif tenure < 365 * 2:
            stage = '成长期'
        elif tenure < 365 * 5:
            stage = '成熟期'
        else:
            stage = '老牌期'

        return {
            'manager_id': m.get('manager_id', ''),
            'name': m.get('name', ''),
            'company': company_name,
            'fund_name': m.get('current_fund_name', ''),
            'fund_code': m.get('current_fund_code', ''),
            'investment_style': m.get('investment_style', '均衡型'),
            'tenure_years': round(tenure / 365, 1),
            'personality_intro': m.get('personality_intro', ''),
            'top_stocks': [s.get('stock_name', '') for s in top_stocks[:5]],
            'main_sectors': main_sectors,
            'sector_description': f"重点布局{main_sectors[0] if main_sectors else '综合'}行业" if main_sectors else "",
            'holdings_count': len(top_stocks),
            'fund_stage': stage,
            'stage_description': self.stage_templates.get(stage, ''),
            'strengths': self._extract_strengths(m),
            'recent_view': m.get('recent_views', [{}])[0].get('views', [''])[0] if m.get('recent_views') else '',
        }

    def _extract_strengths(self, m):
        """提取优势"""
        strengths = []
        style = m.get('investment_style', '均衡型')
        tenure = m.get('tenure_days', 0)

        if tenure > 365 * 5:
            strengths.append(f"任职{tenure//365}年，经验丰富")
        elif tenure > 365 * 3:
            strengths.append(f"任职近{tenure//365}年，风格成熟")

        if m.get('top_stocks'):
            strengths.append("有持仓数据，透明度高")

        if style == '成长型':
            strengths.append("成长风格，进攻性强")
        elif style == '价值型':
            strengths.append("价值风格，注重风控")
        else:
            strengths.append("均衡风格，稳健运作")

        return strengths[:2]

    def generate_all_reports(self):
        """为所有公司生成报告"""
        print("=" * 60)
        print("开始生成所有基金公司的完整分析报告")
        print("=" * 60)

        companies, managers = self.load_data()
        print(f"公司数: {len(companies)}, 经理数: {len(managers)}")

        all_reports = []
        stats = {'with_holdings': 0, 'total_managers': 0, 'top_managers_found': 0}

        for i, company in enumerate(companies):
            company_name = company['name']
            company_short = company.get('short_name', company_name)

            # 匹配该公司经理
            company_managers = []
            for m in managers:
                m_company = m.get('company_name', '')
                m_short = m_company.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '')
                c_short = company_short.replace('基金管理有限公司', '').replace('基金有限公司', '').replace('股份有限公司', '')
                if m_company == company_name or m_short == c_short or c_short == m_short:
                    company_managers.append(m)

            stats['total_managers'] += len(company_managers)

            # 风格分布
            style_dist = Counter(m.get('investment_style', '均衡型') for m in company_managers)
            dominant_style = style_dist.most_common(1)[0][0] if style_dist else '均衡型'

            # 行业分布
            all_sectors = []
            for m in company_managers:
                for s in m.get('top_stocks', []):
                    sec = self.detect_sector(s.get('stock_name', ''))
                    if sec:
                        all_sectors.append(sec)
            sector_counter = Counter(all_sectors)
            top_sectors = [s for s, _ in sector_counter.most_common(5)]

            # 找头牌经理（3年以上任期+有持仓）
            qualified = [m for m in company_managers if m.get('tenure_days', 0) > 365 * 3 and m.get('top_stocks')]
            qualified.sort(key=lambda x: -x.get('tenure_days', 0))

            top_manager = None
            if qualified:
                top_manager = self.analyze_manager(qualified[0], company_name)
                stats['top_managers_found'] += 1
                stats['with_holdings'] += 1
            elif [m for m in company_managers if m.get('top_stocks')]:
                # 有持仓但任期不足3年
                with_holdings = [m for m in company_managers if m.get('top_stocks')][0]
                top_manager = self.analyze_manager(with_holdings, company_name)
                stats['with_holdings'] += 1

            # 公司产品分布
            style_dist_full = {}
            for style, count in style_dist.items():
                style_dist_full[style] = {
                    'count': count,
                    'percentage': round(count / len(company_managers) * 100, 1) if company_managers else 0
                }

            # 特色描述
            highlights = []
            if top_sectors:
                highlights.append(f"重点布局{top_sectors[0]}赛道")
            if style_dist_full:
                top_style = max(style_dist_full.items(), key=lambda x: x[1]['count'])
                style_map = {'成长型': '成长', '价值型': '价值', '均衡型': '均衡'}
                highlights.append(f"{style_map.get(top_style[0], top_style[0])}风格占主导({top_style[1]['percentage']}%)")

            report = {
                'company_id': company.get('company_id', ''),
                'name': company_name,
                'short_name': company_short,
                'total_scale': company.get('total_scale', 0),
                'manager_count': len(company_managers),
                'dominant_style': dominant_style,
                'style_distribution': style_dist_full,
                'top_sectors': top_sectors,
                'highlights': highlights,
                'company_intro': company.get('company_intro', ''),
                'investment_philosophy': company.get('investment_philosophy', ''),
                'culture': company.get('culture', ''),
                'recommendation': company.get('recommendation', ''),
                'slogan': company.get('slogan', ''),
                'top_manager': top_manager,
                'has_holdings_data': len([m for m in company_managers if m.get('top_stocks')]) > 0,
                'star_managers': company.get('star_managers', []),
            }

            all_reports.append(report)

            if (i + 1) % 20 == 0:
                print(f"进度: {i+1}/{len(companies)}")

        # 保存
        output_path = f'{DATA_DIR}/company_reports.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'reports': all_reports,
                'meta': {
                    'total_companies': len(all_reports),
                    'last_update': datetime.now().strftime('%Y-%m-%d'),
                    'stats': stats
                }
            }, f, ensure_ascii=False, indent=2)

        print(f"\n生成完成!")
        print(f"公司报告: {len(all_reports)}")
        print(f"有持仓数据公司: {stats['with_holdings']}")
        print(f"找到头牌经理: {stats['top_managers_found']}")
        print(f"保存至: {output_path}")

        return all_reports


def main():
    generator = CompanyReportGenerator()
    reports = generator.generate_all_reports()

    # 展示示例
    print("\n" + "=" * 60)
    print("示例报告 - 华夏基金")
    print("=" * 60)

    for r in reports:
        if '华夏' in r['name']:
            print(f"\n【公司】{r['name']}")
            print(f"  规模: {r['total_scale']:.0f}亿元")
            print(f"  基金经理: {r['manager_count']}位")
            print(f"  主导风格: {r['dominant_style']}")
            print(f"  行业聚焦: {', '.join(r['top_sectors'][:3])}")
            print(f"  特色: {'; '.join(r['highlights'])}")
            print(f"\n  【公司简介】")
            print(f"    {r['company_intro'][:100]}...")
            print(f"\n  【投资理念】")
            print(f"    {r['investment_philosophy'][:80]}...")
            print(f"\n  【投研文化】")
            print(f"    {r['culture'][:80]}...")

            if r['top_manager']:
                tm = r['top_manager']
                print(f"\n  【头牌经理】{tm['name']}")
                print(f"    管理基金: {tm['fund_name']}")
                print(f"    风格: {tm['investment_style']}, 任期: {tm['tenure_years']}年")
                print(f"    重仓股: {', '.join(tm['top_stocks'][:3])}")
                print(f"    行业: {tm['sector_description']}")
                print(f"    优势: {', '.join(tm['strengths'])}")
                print(f"    阶段: {tm['fund_stage']} - {tm['stage_description'][:50]}...")
            else:
                print(f"\n  【头牌经理】暂无持仓数据")

            print(f"\n  【产品亮点】")
            for h in r['highlights']:
                print(f"    • {h}")

            break

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()