import pandas as pd
from datetime import datetime
from data_fetcher import DataFetcher
from kline_plotter import KLinePlotter
import argparse

def main():
    parser = argparse.ArgumentParser(description='K线图绘制工具 - 支持日线、周线、月线切换')
    parser.add_argument(
        '-t', '--timeframe',
        type=str,
        default='1d',
        choices=['1d', '1w', '1m'],
        help='时间周期：1d=日线，1w=周线，1m=月线（默认：1d）'
    )
    parser.add_argument(
        '-s', '--symbol',
        type=str,
        default='AAPL',
        help='股票代码（默认：AAPL）'
    )
    parser.add_argument(
        '--no-boll',
        action='store_true',
        help='不显示布林带'
    )
    parser.add_argument(
        '--no-rsi',
        action='store_true',
        help='不显示RSI指标'
    )
    parser.add_argument(
        '--no-volume',
        action='store_true',
        help='不显示成交量'
    )
    parser.add_argument(
        '-p', '--period',
        type=str,
        default='1y',
        help='数据周期：1y=1年，2y=2年，5y=5年（默认：1y）'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='不使用缓存，强制从网络获取'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("K线图绘制工具")
    print("=" * 60)
    
    timeframe_names = {
        '1d': '日线',
        '1w': '周线',
        '1m': '月线'
    }
    
    print(f"\n股票代码: {args.symbol}")
    print(f"时间周期: {timeframe_names[args.timeframe]} ({args.timeframe})")
    print(f"数据周期: {args.period}")
    print(f"使用缓存: {'否' if args.no_cache else '是'}")
    
    # 初始化
    fetcher = DataFetcher(cache_dir='data_cache', cache_days=1)
    plotter = KLinePlotter(style='charles')
    
    # 获取真实数据
    print(f"\n正在获取 {args.symbol} 的数据...")
    use_cache = not args.no_cache
    daily_data = fetcher.fetch_stock_data(
        args.symbol,
        period=args.period,
        use_cache=use_cache
    )
    
    print(f"✓ 成功获取 {len(daily_data)} 条日线数据")
    
    # 转换为指定周期
    if args.timeframe == '1d':
        data = daily_data
        print(f"✓ 使用日线数据: {len(data)} 条")
    elif args.timeframe == '1w':
        print(f"\n正在转换为周线数据...")
        data = fetcher.resample_data(daily_data, timeframe='1w')
        print(f"✓ 周线数据: {len(data)} 条")
    elif args.timeframe == '1m':
        print(f"\n正在转换为月线数据...")
        data = fetcher.resample_data(daily_data, timeframe='1m')
        print(f"✓ 月线数据: {len(data)} 条")
    
    print(f"✓ 时间范围: {data.index[0].date()} 到 {data.index[-1].date()}")
    print(f"✓ 最新收盘价: ${data['Close'].iloc[-1]:.2f}")
    print(f"✓ 最高价: ${data['High'].max():.2f}")
    print(f"✓ 最低价: ${data['Low'].min():.2f}")
    
    # 设置布林带参数（根据周期调整）
    if args.timeframe == '1d':
        boll_period = 20
    elif args.timeframe == '1w':
        boll_period = 10
    else:
        boll_period = 5
    
    # 绘制K线图
    print(f"\n正在绘制K线图...")
    print(f"  - 布林带: {'显示' if not args.no_boll else '不显示'}")
    print(f"  - 成交量: {'显示' if not args.no_volume else '不显示'}")
    print(f"  - RSI指标: {'显示' if not args.no_rsi else '不显示'}")
    
    plotter.plot_with_indicators(
        data,
        title=f'{args.symbol} {timeframe_names[args.timeframe]}K线图',
        show_boll=not args.no_boll,
        show_rsi=not args.no_rsi,
        show_volume=not args.no_volume,
        boll_period=boll_period,
        boll_std=2,
        rsi_period=14,
        figsize=(16, 12)
    )
    
    print("\n✓ 完成！")
    print("\n使用说明：")
    print("  python kline_tool.py -t 1d           # 绘制日线图")
    print("  python kline_tool.py -t 1w           # 绘制周线图")
    print("  python kline_tool.py -t 1m           # 绘制月线图")
    print("  python kline_tool.py -s MSFT         # 指定股票代码")
    print("  python kline_tool.py -p 2y           # 指定数据周期（2年）")
    print("  python kline_tool.py --no-cache      # 不使用缓存，强制从网络获取")
    print("  python kline_tool.py --no-boll       # 不显示布林带")
    print("  python kline_tool.py --no-rsi        # 不显示RSI")
    print("  python kline_tool.py --no-volume     # 不显示成交量")
    print("\n交互式查看器（支持鼠标拖拽、缩放、悬停查看）：")
    print("  python interactive_kline.py -s AAPL")
    print("\n组合使用示例：")
    print("  python kline_tool.py -t 1w -s GOOGL")
    print("  python kline_tool.py -t 1d -s AAPL -p 5y --no-boll")
    print("  python kline_tool.py --no-cache -t 1d -s MSFT")

if __name__ == '__main__':
    main()
