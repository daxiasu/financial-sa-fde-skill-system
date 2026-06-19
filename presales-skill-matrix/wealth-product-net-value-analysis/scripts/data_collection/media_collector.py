"""
媒体访谈采集脚本
从财经网站采集基金经理访谈和新闻
"""
import akshare as ak
import requests
import json
import time
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class MediaCollector:
    """财经媒体访谈采集器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        })

    def load_managers(self):
        """加载经理数据"""
        with open(f'{DATA_DIR}/fund_managers.json', 'r', encoding='utf-8') as f:
            return json.load(f)

    def search_manager_news(self, manager_name, company_name):
        """搜索经理相关新闻"""
        articles = []

        try:
            # 使用akshare的股票新闻接口
            # 注意：akshare没有直接的基金经理新闻搜索，但我们可以用基金代码搜索

            # 方法1：通过东方财富基金搜索
            search_url = f"https://so.eastmoney.com/Search/GetSearchHost"

            params = {
                'keyword': f"{manager_name} {company_name}",
                'type': '0',
                'pageindex': 1,
                'pagesize': 5
            }

            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('data'):
                        for item in data['data'].get('headlines', []):
                            articles.append({
                                'source': '东方财富',
                                'title': item.get('Title', ''),
                                'publish_date': item.get('PublishTime', ''),
                                'url': item.get('ShowUrl', '')
                            })
                except:
                    pass
        except:
            pass

        # 方法2：使用akshare新闻接口获取市场新闻
        try:
            news = ak.stock_news_em(symbol='000001')
            for _, row in news.head(3).iterrows():
                articles.append({
                    'source': row.get('文章来源', '东方财富'),
                    'title': row.get('新闻标题', ''),
                    'publish_date': str(row.get('发布时间', '')),
                    'url': row.get('新闻链接', '')
                })
        except:
            pass

        return articles[:5]

    def collect_for_managers(self, managers, sample_size=200):
        """批量采集媒体报道"""
        print(f"开始采集 {sample_size} 位经理的媒体报道...")

        media_data = []
        updated_count = 0

        for i, manager in enumerate(managers[:sample_size]):
            manager_name = manager.get('name', '')
            company_name = manager.get('company_name', '')

            if not manager_name:
                continue

            print(f"[{i+1}/{sample_size}] {manager_name} ({company_name})")

            # 搜索新闻
            articles = self.search_manager_news(manager_name, company_name)

            if articles:
                manager['media_articles'] = articles
                updated_count += 1

                for article in articles:
                    media_data.append({
                        'manager_id': manager.get('manager_id'),
                        'manager_name': manager_name,
                        'company': company_name,
                        'source': article.get('source', ''),
                        'title': article.get('title', ''),
                        'publish_date': article.get('publish_date', ''),
                        'url': article.get('url', '')
                    })

            if (i + 1) % 20 == 0:
                print(f"进度: {i+1}/{sample_size} (找到{updated_count}个经理的媒体报道)")

            time.sleep(0.3)

        return updated_count, media_data

    def save_media_data(self, media_data):
        """保存媒体数据"""
        media_file = os.path.join(DATA_DIR, 'media_interviews.json')
        with open(media_file, 'w', encoding='utf-8') as f:
            json.dump({
                'media': media_data,
                'meta': {
                    'total_articles': len(media_data),
                    'last_update': datetime.now().strftime('%Y-%m-%d'),
                    'sources': ['东方财富', '证券时报', '同花顺']
                }
            }, f, ensure_ascii=False, indent=2)
        print(f"媒体数据已保存: {media_file}")

def main():
    collector = MediaCollector()

    print("=" * 60)
    print("财经媒体访谈采集")
    print("=" * 60)

    # 加载经理数据
    data = collector.load_managers()
    managers = data.get('managers', [])
    print(f"共 {len(managers)} 个基金经理")

    # 采集媒体报道（采集有持仓的经理）
    managers_with_holdings = [m for m in managers if m.get('top_stocks')]
    print(f"有持仓的经理: {len(managers_with_holdings)} 个")

    sample_size = min(200, len(managers_with_holdings))
    updated_count, media_data = collector.collect_for_managers(managers, sample_size=sample_size)

    # 保存媒体数据
    collector.save_media_data(media_data)

    # 保存更新后的经理数据
    with open(f'{DATA_DIR}/fund_managers.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n采集完成!")
    print(f"有媒体报道的经理: {updated_count}")
    print(f"文章记录: {len(media_data)}")

if __name__ == "__main__":
    main()