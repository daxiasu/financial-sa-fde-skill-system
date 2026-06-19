"""
天天基金网数据采集脚本
从天天基金网采集基金经理、持仓等数据
"""
import requests
import json
import re
import time
from bs4 import BeautifulSoup
import pandas as pd

class EastMoneyCollector:
    """天天基金数据采集器"""

    def __init__(self):
        self.base_url = "https://fund.eastmoney.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://fund.eastmoney.com/'
        })

    def get_all_managers(self, fund_type='all', page=1, page_size=50):
        """
        获取基金经理列表

        参数:
            fund_type: all/gp/hh/zq/sy (全部/股票/混合/债券/收益)
            page: 页码
            page_size: 每页数量
        """
        url = "https://fund.eastmoney.com/Data/FundDataPortfolio_Interface.aspx"

        params = {
            'dt': '14',  # 14=基金经理列表
            'ft': fund_type,
            'pn': page_size,
            'pi': page,
            'sc': 'abbname',
            'st': 'asc',
            'mc': 'returnjson'
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            text = response.text

            # 解析JavaScript变量格式
            match = re.search(r'returnjson\s*=\s*(\{.*?\});', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return self._parse_manager_list(data)

        except Exception as e:
            print(f"获取经理列表失败: {e}")

        return []

    def _parse_manager_list(self, data):
        """解析经理列表数据"""
        managers = []

        try:
            items = data.get('data', []) or data.get('list', [])
            for item in items:
                manager = {
                    'manager_id': str(item.get('id', '')),
                    'name': item.get('name', ''),
                    'company_id': item.get('companyid', ''),
                    'company_name': item.get('company', ''),
                    'fund_count': item.get('fundcount', 0),
                    'total_scale': item.get('totalscale', 0),
                    'incept_date': item.get('incepdate', '')
                }
                managers.append(manager)
        except Exception as e:
            print(f"解析数据失败: {e}")

        return managers

    def get_manager_detail(self, manager_id):
        """
        获取基金经理详情

        参数:
            manager_id: 经理代码
        """
        url = f"https://fund.eastmoney.com/manager/{manager_id}.html"

        try:
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')

            detail = {}

            # 姓名和基本信息
            name_elem = soup.find('div', class_='name')
            if name_elem:
                detail['name'] = name_elem.get_text().strip()

            # 基本信息卡片
            info_box = soup.find('div', class_='info-box')
            if info_box:
                lis = info_box.find_all('li')
                for li in lis:
                    text = li.get_text()
                    if '管理规模' in text:
                        detail['scale'] = re.search(r'[\d.]+', text).group()
                    elif '任职时间' in text:
                        detail['tenure'] = re.search(r'\d+年', text).group()

            # 管理基金列表
            fund_table = soup.find('table', class_='fund-table')
            if fund_table:
                funds = []
                rows = fund_table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        fund = {
                            'code': cols[0].get_text().strip(),
                            'name': cols[1].get_text().strip(),
                            'type': cols[2].get_text().strip(),
                            'scale': cols[3].get_text().strip(),
                            'tenure': cols[4].get_text().strip()
                        }
                        funds.append(fund)
                detail['fund_list'] = funds

            return detail

        except Exception as e:
            print(f"获取经理详情失败: {e}")
            return {}

    def get_fund_holdings(self, fund_code):
        """
        获取基金持仓数据（十大股票、十大债券）

        参数:
            fund_code: 基金代码
        """
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"

        try:
            response = self.session.get(url, timeout=30)
            text = response.text

            holdings = {}

            # 解析股票代码
            stock_match = re.search(r'stockCodes\s*=\s*\[(.*?)\]', text)
            if stock_match:
                codes = re.findall(r'["\'](\d+)["\']', stock_match.group(1))
                holdings['stock_codes'] = codes

            # 解析债券代码
            bond_match = re.search(r'zqCodes\s*=\s*["\'](.*?)["\']', text)
            if bond_match:
                codes = bond_match.group(1).split(',')
                holdings['bond_codes'] = [c.strip() for c in codes if c.strip()]

            # 解析持仓权重（从JS变量中提取）
            # 实际权重需要从定期报告中获取

            return holdings

        except Exception as e:
            print(f"获取持仓失败: {e}")
            return {}

    def get_fund_info(self, fund_code):
        """
        获取基金基本信息
        """
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"

        try:
            response = self.session.get(url, timeout=30)
            text = response.text

            info = {}

            # 基金名称
            name_match = re.search(r'fS_name\s*=\s*["\'](.*?)["\']', text)
            if name_match:
                info['name'] = name_match.group(1)

            # 基金代码
            info['code'] = fund_code

            # 收益率数据
            for period in ['1n', '6y', '3y', '1y', '1m']:
                match = re.search(rf'syl_{period}\s*=\s*["\']?([\d.]+)["\']?', text)
                if match:
                    info[f'return_{period}'] = float(match.group(1))

            return info

        except Exception as e:
            return {}

    def save_managers(self, managers, filepath):
        """保存经理数据到JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({'managers': managers, 'meta': {
                'total_count': len(managers),
                'last_update': time.strftime('%Y-%m-%d'),
                'source': '天天基金网'
            }}, f, ensure_ascii=False, indent=2)

def main():
    collector = EastMoneyCollector()

    print("正在采集基金经理列表...")

    all_managers = []
    for fund_type in ['all', 'gp', 'hh', 'zq', 'sy']:
        managers = collector.get_all_managers(fund_type=fund_type, page=1)
        all_managers.extend(managers)
        print(f"{fund_type}: 获取 {len(managers)} 位经理")
        time.sleep(1)

    # 去重
    seen = set()
    unique_managers = []
    for m in all_managers:
        if m['manager_id'] not in seen:
            seen.add(m['manager_id'])
            unique_managers.append(m)

    print(f"\n共获取 {len(unique_managers)} 位基金经理")

    if unique_managers:
        collector.save_managers(unique_managers, '../data/fund_managers.json')
        print("数据已保存到 ../data/fund_managers.json")

if __name__ == "__main__":
    main()