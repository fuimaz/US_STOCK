import pandas as pd
from datetime import datetime
from data.data_fetcher import DataFetcher
from visualization.kline_plotter import KLinePlotter
import argparse

def main():
    parser = argparse.ArgumentParser(description='K绾垮浘缁樺埗宸ュ叿 - 鏀寔鏃ョ嚎銆佸懆绾裤€佹湀绾垮垏鎹?)
    parser.add_argument(
        '-t', '--timeframe',
        type=str,
        default='1d',
        choices=['1d', '1w', '1m'],
        help='鏃堕棿鍛ㄦ湡锛?d=鏃ョ嚎锛?w=鍛ㄧ嚎锛?m=鏈堢嚎锛堥粯璁わ細1d锛?
    )
    parser.add_argument(
        '-s', '--symbol',
        type=str,
        default='AAPL',
        help='鑲＄エ浠ｇ爜锛堥粯璁わ細AAPL锛?
    )
    parser.add_argument(
        '--no-boll',
        action='store_true',
        help='涓嶆樉绀哄竷鏋楀甫'
    )
    parser.add_argument(
        '--no-rsi',
        action='store_true',
        help='涓嶆樉绀篟SI鎸囨爣'
    )
    parser.add_argument(
        '--no-volume',
        action='store_true',
        help='涓嶆樉绀烘垚浜ら噺'
    )
    parser.add_argument(
        '-p', '--period',
        type=str,
        default='1y',
        help='鏁版嵁鍛ㄦ湡锛?y=1骞达紝2y=2骞达紝5y=5骞达紙榛樿锛?y锛?
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='涓嶄娇鐢ㄧ紦瀛橈紝寮哄埗浠庣綉缁滆幏鍙?
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("K绾垮浘缁樺埗宸ュ叿")
    print("=" * 60)
    
    timeframe_names = {
        '1d': '鏃ョ嚎',
        '1w': '鍛ㄧ嚎',
        '1m': '鏈堢嚎'
    }
    
    print(f"\n鑲＄エ浠ｇ爜: {args.symbol}")
    print(f"鏃堕棿鍛ㄦ湡: {timeframe_names[args.timeframe]} ({args.timeframe})")
    print(f"鏁版嵁鍛ㄦ湡: {args.period}")
    print(f"浣跨敤缂撳瓨: {'鍚? if args.no_cache else '鏄?}")
    
    # 鍒濆鍖?    fetcher = DataFetcher(cache_dir='data_cache', cache_days=1)
    plotter = KLinePlotter(style='charles')
    
    # 鑾峰彇鐪熷疄鏁版嵁
    print(f"\n姝ｅ湪鑾峰彇 {args.symbol} 鐨勬暟鎹?..")
    use_cache = not args.no_cache
    daily_data = fetcher.fetch_stock_data(
        args.symbol,
        period=args.period,
        use_cache=use_cache
    )
    
    print(f"鉁?鎴愬姛鑾峰彇 {len(daily_data)} 鏉℃棩绾挎暟鎹?)
    
    # 杞崲涓烘寚瀹氬懆鏈?    if args.timeframe == '1d':
        data = daily_data
        print(f"鉁?浣跨敤鏃ョ嚎鏁版嵁: {len(data)} 鏉?)
    elif args.timeframe == '1w':
        print(f"\n姝ｅ湪杞崲涓哄懆绾挎暟鎹?..")
        data = fetcher.resample_data(daily_data, timeframe='1w')
        print(f"鉁?鍛ㄧ嚎鏁版嵁: {len(data)} 鏉?)
    elif args.timeframe == '1m':
        print(f"\n姝ｅ湪杞崲涓烘湀绾挎暟鎹?..")
        data = fetcher.resample_data(daily_data, timeframe='1m')
        print(f"鉁?鏈堢嚎鏁版嵁: {len(data)} 鏉?)
    
    print(f"鉁?鏃堕棿鑼冨洿: {data.index[0].date()} 鍒?{data.index[-1].date()}")
    print(f"鉁?鏈€鏂版敹鐩樹环: ${data['Close'].iloc[-1]:.2f}")
    print(f"鉁?鏈€楂樹环: ${data['High'].max():.2f}")
    print(f"鉁?鏈€浣庝环: ${data['Low'].min():.2f}")
    
    # 璁剧疆甯冩灄甯﹀弬鏁帮紙鏍规嵁鍛ㄦ湡璋冩暣锛?    if args.timeframe == '1d':
        boll_period = 20
    elif args.timeframe == '1w':
        boll_period = 10
    else:
        boll_period = 5
    
    # 缁樺埗K绾垮浘
    print(f"\n姝ｅ湪缁樺埗K绾垮浘...")
    print(f"  - 甯冩灄甯? {'鏄剧ず' if not args.no_boll else '涓嶆樉绀?}")
    print(f"  - 鎴愪氦閲? {'鏄剧ず' if not args.no_volume else '涓嶆樉绀?}")
    print(f"  - RSI鎸囨爣: {'鏄剧ず' if not args.no_rsi else '涓嶆樉绀?}")
    
    plotter.plot_with_indicators(
        data,
        title=f'{args.symbol} {timeframe_names[args.timeframe]}K绾垮浘',
        show_boll=not args.no_boll,
        show_rsi=not args.no_rsi,
        show_volume=not args.no_volume,
        boll_period=boll_period,
        boll_std=2,
        rsi_period=14,
        figsize=(16, 12)
    )
    
    print("\n鉁?瀹屾垚锛?)
    print("\n浣跨敤璇存槑锛?)
    print("  python kline_tool.py -t 1d           # 缁樺埗鏃ョ嚎鍥?)
    print("  python kline_tool.py -t 1w           # 缁樺埗鍛ㄧ嚎鍥?)
    print("  python kline_tool.py -t 1m           # 缁樺埗鏈堢嚎鍥?)
    print("  python kline_tool.py -s MSFT         # 鎸囧畾鑲＄エ浠ｇ爜")
    print("  python kline_tool.py -p 2y           # 鎸囧畾鏁版嵁鍛ㄦ湡锛?骞达級")
    print("  python kline_tool.py --no-cache      # 涓嶄娇鐢ㄧ紦瀛橈紝寮哄埗浠庣綉缁滆幏鍙?)
    print("  python kline_tool.py --no-boll       # 涓嶆樉绀哄竷鏋楀甫")
    print("  python kline_tool.py --no-rsi        # 涓嶆樉绀篟SI")
    print("  python kline_tool.py --no-volume     # 涓嶆樉绀烘垚浜ら噺")
    print("\n浜や簰寮忔煡鐪嬪櫒锛堟敮鎸侀紶鏍囨嫋鎷姐€佺缉鏀俱€佹偓鍋滄煡鐪嬶級锛?)
    print("  python interactive_kline.py -s AAPL")
    print("\n缁勫悎浣跨敤绀轰緥锛?)
    print("  python kline_tool.py -t 1w -s GOOGL")
    print("  python kline_tool.py -t 1d -s AAPL -p 5y --no-boll")
    print("  python kline_tool.py --no-cache -t 1d -s MSFT")

if __name__ == '__main__':
    main()


