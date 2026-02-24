"""
绘制期货K线图，显示缠论买卖点和BOLL指标
"""
import pandas as pd
import numpy as np
import os
import sys
import warnings
warnings.filterwarnings('ignore')

from chan_theory_realtime import ChanTheoryRealtime
from kline_plotter import KLinePlotter


# 期货合约配置
CONTRACT_SPECS = {
    'TA0': {'name': 'PTA'},
    'I0': {'name': '铁矿石'},
    'Y0': {'name': '豆油'},
    'M0': {'name': '豆粕'},
}


def load_futures_data(symbol: str, data_dir: str = 'data_cache/china_futures') -> pd.DataFrame:
    """加载期货分钟数据"""
    file_path = os.path.join(data_dir, f'{symbol}_5min.csv')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"数据文件不存在: {file_path}")
    
    df = pd.read_csv(file_path)
    
    if 'datetime' in df.columns:
        df['DateTime'] = pd.to_datetime(df['datetime'])
    elif 'DateTime' not in df.columns:
        df['DateTime'] = df.index
    
    column_mapping = {
        'open': 'Open', 'high': 'High', 'low': 'Low', 
        'close': 'Close', 'volume': 'Volume'
    }
    df = df.rename(columns=column_mapping)
    
    df.set_index('DateTime', inplace=True)
    df.sort_index(inplace=True)
    
    return df


def analyze_and_plot(symbol: str, output_dir: str = 'results/futures_signals'):
    """分析并绘制K线图"""
    print(f"\n{'='*50}")
    print(f"处理 {symbol}...")
    
    # 加载数据
    df = load_futures_data(symbol)
    contract_name = CONTRACT_SPECS.get(symbol, {}).get('name', symbol)
    
    print(f"数据范围: {df.index[0]} ~ {df.index[-1]}")
    print(f"数据条数: {len(df)}")
    
    # 缠论分析
    chan = ChanTheoryRealtime(k_type='minute')
    result_df = chan.analyze(df)
    
    # 生成买卖信号 - 使用float类型避免类型错误
    buy_signals = pd.Series(0.0, index=df.index, dtype=float)
    sell_signals = pd.Series(0.0, index=df.index, dtype=float)
    
    for i in range(1, len(result_df)):
        current = result_df.iloc[i]
        previous = result_df.iloc[i-1]
        
        # 只取最后一个时间点对应的原始数据索引
        if i < len(df):
            idx = df.index[i]
            
            if current['buy_point'] > 0 and previous['buy_point'] == 0:
                buy_signals.loc[idx] = float(df.loc[idx, 'Close'])
            
            if current['sell_point'] > 0 and previous['sell_point'] == 0:
                sell_signals.loc[idx] = float(df.loc[idx, 'Close'])
    
    # 统计信号数量
    buy_count = int((buy_signals > 0).sum())
    sell_count = int((sell_signals > 0).sum())
    
    # 绘制K线图
    plotter = KLinePlotter(style='charles')
    
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, f'{symbol}_kline.png')
    
    print(f"正在绘制K线图...")
    
    plotter.plot_with_signals_and_indicators(
        data=df,
        buy_signals=buy_signals,
        sell_signals=sell_signals,
        title=f"{contract_name}({symbol}) 5分钟K线 - 缠论买卖点",
        show_boll=True,
        show_rsi=False,
        show_volume=True,
        boll_period=20,
        boll_std=2,
        save_path=save_path
    )
    
    print(f"图片已保存: {save_path}")
    
    return {
        'symbol': symbol,
        'name': contract_name,
        'data': df,
        'result': result_df,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'buy_count': buy_count,
        'sell_count': sell_count
    }


if __name__ == '__main__':
    # 要分析的合约列表
    symbols = ['TA0', 'I0', 'Y0', 'M0']
    
    # 可以通过命令行参数指定
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
    
    print("=" * 60)
    print("期货K线图绘制 - 缠论买卖点 + BOLL指标")
    print("=" * 60)
    
    results = []
    for symbol in symbols:
        if symbol in CONTRACT_SPECS:
            try:
                result = analyze_and_plot(symbol)
                results.append(result)
            except Exception as e:
                print(f"处理 {symbol} 失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"未知合约: {symbol}")
    
    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)
    
    for r in results:
        print(f"  {r['symbol']} ({r['name']}): {r['buy_count']} 个买入信号, {r['sell_count']} 个卖出信号")
