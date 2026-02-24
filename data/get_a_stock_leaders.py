"""
获取A股各行业龙头近20年数据并保存到缓存
"""
from data_fetcher import DataFetcher
import pandas as pd


def get_a_stock_sector_leaders():
    """
    获取A股各行业龙头近20年数据
    """
    print("=" * 100)
    print("获取A股各行业龙头近20年数据")
    print("=" * 100)
    print()
    
    # 初始化数据获取器
    fetcher = DataFetcher(
        cache_dir='data_cache',
        cache_days=365,
        proxy='http://127.0.0.1:7897',
        retry_count=5,
        retry_delay=5.0
    )
    
    # A股各行业龙头股票列表
    sector_leaders = [
        # 白酒
        ('600519.SS', '贵州茅台', '白酒'),
        ('000858.SZ', '五粮液', '白酒'),
        ('000568.SZ', '泸州老窖', '白酒'),
        
        # 银行
        ('600036.SS', '招商银行', '银行'),
        ('000001.SZ', '平安银行', '银行'),
        ('601398.SS', '工商银行', '银行'),
        ('601939.SS', '建设银行', '银行'),
        ('601166.SS', '兴业银行', '银行'),
        
        # 保险
        ('601318.SS', '中国平安', '保险'),
        ('601601.SS', '中国太保', '保险'),
        ('601628.SS', '中国人寿', '保险'),
        
        # 证券
        ('600030.SS', '中信证券', '证券'),
        ('601688.SS', '华泰证券', '证券'),
        
        # 医药
        ('600276.SS', '恒瑞医药', '医药'),
        ('603259.SS', '药明康德', '医药'),
        ('300760.SZ', '迈瑞医疗', '医药'),
        ('000661.SZ', '长春高新', '医药'),
        
        # 新能源
        ('300750.SZ', '宁德时代', '新能源'),
        ('002594.SZ', '比亚迪', '新能源'),
        ('601012.SS', '隆基绿能', '新能源'),
        ('300274.SZ', '阳光电源', '新能源'),
        ('002460.SZ', '赣锋锂业', '新能源'),
        
        # 房地产
        ('000002.SZ', '万科A', '房地产'),
        ('600048.SS', '保利发展', '房地产'),
        
        # 汽车制造
        ('600104.SS', '上汽集团', '汽车制造'),
        ('000625.SZ', '长安汽车', '汽车制造'),
        ('601238.SS', '广汽集团', '汽车制造'),
        
        # 钢铁
        ('600019.SS', '宝钢股份', '钢铁'),
        
        # 有色金属
        ('601899.SS', '紫金矿业', '有色金属'),
        ('601600.SS', '中国铝业', '有色金属'),
        
        # 煤炭
        ('601088.SS', '中国神华', '煤炭'),
        ('601898.SS', '中煤能源', '煤炭'),
        
        # 石油石化
        ('601857.SS', '中国石油', '石油石化'),
        ('600028.SS', '中国石化', '石油石化'),
        
        # 化工
        ('600309.SS', '万华化学', '化工'),
        ('600346.SS', '恒力石化', '化工'),
        
        # 家电
        ('000651.SZ', '格力电器', '家电'),
        ('000333.SZ', '美的集团', '家电'),
        ('600690.SS', '海尔智家', '家电'),
        
        # 食品饮料
        ('603288.SS', '海天味业', '食品饮料'),
        ('600887.SS', '伊利股份', '食品饮料'),
        ('002304.SZ', '洋河股份', '食品饮料'),
        
        # 电子
        ('000725.SZ', '京东方A', '电子'),
        ('002475.SZ', '立讯精密', '电子'),
        ('600584.SS', '长电科技', '电子'),
        
        # 通信
        ('600941.SS', '中国移动', '通信'),
        ('600050.SS', '中国联通', '通信'),
        
        # 电力
        ('600900.SS', '长江电力', '电力'),
        ('601985.SS', '中国核电', '电力'),
        ('600886.SS', '国投电力', '电力'),
        
        # 航空
        ('601111.SS', '中国国航', '航空'),
        ('600029.SS', '南方航空', '航空'),
        ('600115.SS', '东方航空', '航空'),
        
        # 机场
        ('600009.SS', '上海机场', '机场'),
        
        # 港口
        ('600018.SS', '上港集团', '港口'),
        
        # 基建
        ('601390.SS', '中国中铁', '基建'),
        ('601186.SS', '中国铁建', '基建'),
        
        # 机械
        ('000333.SZ', '三一重工', '机械'),
        ('600031.SS', '徐工机械', '机械'),
        
        # 建材
        ('600585.SS', '海螺水泥', '建材'),
        
        # 农业
        ('000876.SZ', '新希望', '农业'),
        ('002714.SZ', '牧原股份', '农业'),
        
        # 零售
        ('601888.SS', '中国中免', '零售'),
        ('600694.SS', '大商股份', '零售'),
        
        # 软件
        ('300033.SZ', '同花顺', '软件'),
        ('002415.SZ', '海康威视', '软件'),
        
        # 半导体
        ('688981.SH', '中芯国际', '半导体'),
        ('002049.SZ', '紫光国微', '半导体'),
    ]
    
    period = '20y'
    adjust = 'forward'
    
    results = []
    success_count = 0
    fail_count = 0
    
    for symbol, name, sector in sector_leaders:
        print(f"正在获取 {name} ({symbol}) - {sector}...")
        print("-" * 100)
        
        try:
            # 获取日线数据
            data = fetcher.fetch_stock_data(symbol, period=period, adjust=adjust)
            
            if data is not None and len(data) > 0:
                print(f"✓ 数据获取成功")
                print(f"  行业: {sector}")
                print(f"  数据量: {len(data)} 条")
                print(f"  时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
                print(f"  最新收盘价: ¥{data['Close'].iloc[-1]:.2f}")
                print(f"  最新成交量: {data['Volume'].iloc[-1]:,.0f}")
                
                # 计算基本统计
                first_close = data['Close'].iloc[0]
                last_close = data['Close'].iloc[-1]
                total_return = ((last_close - first_close) / first_close) * 100
                
                # 计算年化收益
                years = len(data) / 252
                annualized_return = (1 + total_return / 100) ** (1 / years) - 1
                annualized_return_pct = annualized_return * 100
                
                print(f"  20年总涨幅: {total_return:.2f}%")
                print(f"  年化收益: {annualized_return_pct:.2f}%")
                
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'sector': sector,
                    'status': '成功',
                    'data_count': len(data),
                    'start_date': data.index[0].strftime('%Y-%m-%d'),
                    'end_date': data.index[-1].strftime('%Y-%m-%d'),
                    'latest_price': data['Close'].iloc[-1],
                    'latest_volume': data['Volume'].iloc[-1],
                    'total_return': total_return,
                    'annualized_return': annualized_return_pct
                })
                
                success_count += 1
            else:
                print(f"✗ 未获取到数据")
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'sector': sector,
                    'status': '无数据',
                    'data_count': 0,
                    'start_date': None,
                    'end_date': None,
                    'latest_price': None,
                    'latest_volume': None,
                    'total_return': None,
                    'annualized_return': None
                })
                fail_count += 1
        except Exception as e:
            print(f"✗ 获取失败: {e}")
            results.append({
                'symbol': symbol,
                'name': name,
                'sector': sector,
                'status': f'失败: {str(e)}',
                'data_count': 0,
                'start_date': None,
                'end_date': None,
                'latest_price': None,
                'latest_volume': None,
                'total_return': None,
                'annualized_return': None
            })
            fail_count += 1
        
        print()
    
    # 打印汇总结果
    print("=" * 100)
    print("获取结果汇总")
    print("=" * 100)
    print()
    print(f"{'股票代码':<15} {'股票名称':<12} {'行业':<12} {'状态':<20} {'数据量':<10} {'20年涨幅':<12} {'年化收益':<12}")
    print("-" * 100)
    
    for result in results:
        total_return_str = f"{result['total_return']:.2f}%" if result['total_return'] is not None else "N/A"
        annualized_return_str = f"{result['annualized_return']:.2f}%" if result['annualized_return'] is not None else "N/A"
        print(f"{result['symbol']:<15} {result['name']:<12} {result['sector']:<12} {result['status']:<20} {result['data_count']:<10} {total_return_str:<12} {annualized_return_str:<12}")
    
    print("-" * 100)
    print()
    print(f"✓ 成功获取: {success_count}/{len(sector_leaders)}")
    print(f"✗ 失败: {fail_count}/{len(sector_leaders)}")
    print(f"✓ 成功率: {success_count / len(sector_leaders) * 100:.1f}%")
    print()
    
    # 保存汇总结果
    results_df = pd.DataFrame(results)
    summary_file = 'a_stock_sector_leaders_summary.csv'
    results_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    print(f"✓ 汇总结果已保存到: {summary_file}")
    print()
    
    # 按行业统计
    print("=" * 100)
    print("按行业统计")
    print("=" * 100)
    print()
    
    sector_stats = {}
    for result in results:
        sector = result['sector']
        if sector not in sector_stats:
            sector_stats[sector] = {
                'count': 0,
                'success': 0,
                'total_return': [],
                'annualized_return': []
            }
        
        sector_stats[sector]['count'] += 1
        if result['status'] == '成功':
            sector_stats[sector]['success'] += 1
            sector_stats[sector]['total_return'].append(result['total_return'])
            sector_stats[sector]['annualized_return'].append(result['annualized_return'])
    
    print(f"{'行业':<15} {'股票数':<10} {'成功数':<10} {'成功率':<12} {'平均20年涨幅':<15} {'平均年化收益':<15}")
    print("-" * 90)
    
    for sector in sorted(sector_stats.keys()):
        stats = sector_stats[sector]
        success_rate = stats['success'] / stats['count'] * 100 if stats['count'] > 0 else 0
        
        avg_total_return = sum(stats['total_return']) / len(stats['total_return']) if stats['total_return'] else 0
        avg_annualized_return = sum(stats['annualized_return']) / len(stats['annualized_return']) if stats['annualized_return'] else 0
        
        print(f"{sector:<15} {stats['count']:<10} {stats['success']:<10} {success_rate:<12.1f}% {avg_total_return:<15.2f}% {avg_annualized_return:<15.2f}%")
    
    print("-" * 90)
    print()
    
    # 找出表现最好的股票
    successful_results = [r for r in results if r['status'] == '成功']
    if successful_results:
        best_total_return = max(successful_results, key=lambda x: x['total_return'])
        best_annualized = max(successful_results, key=lambda x: x['annualized_return'])
        
        print("=" * 100)
        print("表现最好的股票")
        print("=" * 100)
        print()
        print(f"✓ 20年涨幅最高: {best_total_return['name']} ({best_total_return['symbol']}) - {best_total_return['total_return']:.2f}%")
        print(f"✓ 年化收益最高: {best_annualized['name']} ({best_annualized['symbol']}) - {best_annualized['annualized_return']:.2f}%")
        print()
    
    print("=" * 100)
    print("数据获取完成！")
    print("=" * 100)


if __name__ == '__main__':
    get_a_stock_sector_leaders()
