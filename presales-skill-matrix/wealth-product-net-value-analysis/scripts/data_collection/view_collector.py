"""
基金经理观点采集脚本
从天天基金网获取2025年报和2026一季报中的基金经理观点
"""
import akshare as ak
import requests
import json
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class ViewCollector:
    """基金经理观点采集器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        })

    def load_managers(self):
        """加载经理数据"""
        with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_managers(self, data):
        """保存经理数据"""
        with open(f'{DATA_DIR}/fund_managers.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_recent_reports(self, fund_code, limit=4):
        """获取最近报告列表"""
        reports = []

        try:
            df = ak.fund_announcement_report_em(symbol=fund_code)

            # 筛选2025年年报和2026年季报
            target_keywords = ['2025年年度报告', '2025年季度报告', '2026年第一季度']
            target_dates = ['2025-12-31', '2026-03-31']

            for _, row in df.iterrows():
                title = row.get('公告标题', '')
                date = str(row.get('公告日期', ''))

                # 筛选最近的报告
                if any(kw in title for kw in ['年度报告', '季度报告', '中期报告']) and date >= '2025-01-01':
                    reports.append({
                        'title': title,
                        'date': date,
                        'fund_name': row.get('基金名称', ''),
                        'report_id': row.get('报告ID', ''),
                        'fund_code': fund_code
                    })

            # 按日期排序，取最新的
            reports.sort(key=lambda x: x['date'], reverse=True)
            reports = reports[:limit]

        except Exception as e:
            pass

        return reports

    def fetch_report_content(self, fund_code, report_title):
        """获取单份报告内容"""
        content = {
            'title': report_title,
            'investment_views': [],
            'market_outlook': '',
            'strategy': ''
        }

        try:
            # 构造天天基金网的报告URL
            # 季报: https://fundf10.eastmoney.com/JJJXXX.html
            # 年报: https://fundf10.eastmoney.com/NDBG.html

            if '年度报告' in report_title:
                url = f"https://fundf10.eastmoney.com/NDBG_{fund_code}.html"
            else:
                url = f"https://fundf10.eastmoney.com/JJJ_{fund_code}.html"

            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 查找报告内容区域
                content_div = soup.find('div', class_='txt_content')
                if not content_div:
                    content_div = soup.find('div', id='ContentBody')

                if content_div:
                    text = content_div.get_text(separator='\n', strip=True)

                    # 提取投资观点（管理人报告章节）
                    patterns = [
                        r'基金经理\s*(?:认为|觉得|表示)?[：:]*\s*([^\n]{20,})',
                        r'(?:看好|关注|投资|配置|布局|机会|风险|策略)[^\n]{10,}',
                        r'运作\s*分析[：:]*\s*([\s\S]*?)(?=重大\s*事项|$)',
                        r'管理人\s*报告[：:]*\s*([\s\S]*?)(?=重大\s*事项|$)',
                        r'投资\s*策略[：:]*\s*([\s\S]*?)(?=重大\s*事项|$)',
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            if len(match) > 20:
                                content['investment_views'].append(match.strip()[:200])

                    # 提取市场展望
                    outlook_patterns = [
                        r'(?:后市\s*展望|市场\s*展望|季度\s*展望)[：:]*\s*([\s\S]*?)(?=重大\s*事项|$)',
                    ]

                    for pattern in outlook_patterns:
                        outlook_match = re.search(pattern, text)
                        if outlook_match:
                            content['market_outlook'] = outlook_match.group(1).strip()[:300]
                            break

                    # 提取投资策略
                    strategy_patterns = [
                        r'(?:投资\s*策略|运作\s*策略)[：:]*\s*([\s\S]*?)(?=重大\s*事项|$)',
                    ]

                    for pattern in strategy_patterns:
                        strategy_match = re.search(pattern, text)
                        if strategy_match:
                            content['strategy'] = strategy_match.group(1).strip()[:300]
                            break

                # 清理重复观点
                seen = set()
                unique_views = []
                for view in content['investment_views']:
                    # 提取前50字符作为去重key
                    key = view[:50].strip()
                    if key and key not in seen:
                        seen.add(key)
                        unique_views.append(view)

                content['investment_views'] = unique_views[:5]

        except Exception as e:
            pass

        return content

    def collect_views_for_managers(self, managers, sample_size=500):
        """批量采集经理观点"""
        print(f"开始采集 {sample_size} 位经理的观点...")

        updated_count = 0
        views_data = []

        for i, manager in enumerate(managers[:sample_size]):
            fund_code = str(manager.get('current_fund_code', ''))
            manager_name = manager.get('name', '')
            company_name = manager.get('company_name', '')

            if not fund_code or len(fund_code) < 6:
                continue

            # 获取最近报告
            reports = self.get_recent_reports(fund_code, limit=4)

            manager_views = []
            for report in reports:
                content = self.fetch_report_content(fund_code, report.get('title', ''))

                if content.get('investment_views') or content.get('market_outlook') or content.get('strategy'):
                    manager_views.append({
                        'report_date': report.get('date', ''),
                        'report_title': report.get('title', ''),
                        'views': content.get('investment_views', []),
                        'outlook': content.get('market_outlook', ''),
                        'strategy': content.get('strategy', '')
                    })

            if manager_views:
                manager['recent_views'] = manager_views
                updated_count += 1

                for view in manager_views:
                    views_data.append({
                        'manager_id': manager.get('manager_id'),
                        'manager_name': manager_name,
                        'company': company_name,
                        'fund_code': fund_code,
                        'fund_name': manager.get('current_fund_name', ''),
                        'report_date': view.get('report_date', ''),
                        'report_title': view.get('report_title', ''),
                        'views': ' '.join(view.get('views', [])),
                        'outlook': view.get('outlook', ''),
                        'strategy': view.get('strategy', '')
                    })

            if (i + 1) % 50 == 0:
                print(f"进度: {i+1}/{sample_size} (已更新{updated_count}个经理)")

            time.sleep(0.4)

        return updated_count, views_data

    def save_views_data(self, views_data):
        """保存观点数据"""
        views_file = os.path.join(DATA_DIR, 'manager_views.json')
        with open(views_file, 'w', encoding='utf-8') as f:
            json.dump({
                'views': views_data,
                'meta': {
                    'total_views': len(views_data),
                    'last_update': datetime.now().strftime('%Y-%m-%d'),
                    'source': '天天基金网',
                    'report_types': ['2025年年报', '2026年一季报']
                }
            }, f, ensure_ascii=False, indent=2)
        print(f"观点数据已保存: {views_file}")

def main():
    collector = ViewCollector()

    print("=" * 60)
    print("基金经理观点采集（2025年报/2026一季报）")
    print("=" * 60)

    # 加载经理数据
    data = collector.load_managers()
    managers = data.get('managers', [])
    print(f"共 {len(managers)} 个基金经理")

    # 采集观点
    # 先采集有持仓的经理，再扩展到全部
    managers_with_holdings = [m for m in managers if m.get('top_stocks')]
    print(f"有持仓的经理: {len(managers_with_holdings)} 个")

    # 采集所有经理的观点
    updated_count, views_data = collector.collect_views_for_managers(managers, sample_size=len(managers))

    # 保存更新后的经理数据
    collector.save_managers(data)

    # 保存观点数据
    collector.save_views_data(views_data)

    print(f"\n采集完成!")
    print(f"更新经理数: {updated_count}")
    print(f"观点记录: {len(views_data)}")

if __name__ == "__main__":
    main()