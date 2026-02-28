"""
方案X：分析周线BOLL策略的赢家 vs 输家特征
找出什么样的股票适合这套策略
"""
import pandas as pd
import numpy as np
import glob
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_stock_characteristics(symbol, data_cache_dir="data_cache"):
    """分析单只股票的特征"""
    try:
        # 读取数据
        cache_file = f"{data_cache_dir}/{symbol}_20y_1d_forward.csv"
        if not os.path.exists(cache_file):
            return None
            
        d = pd.read_csv(cache_file)
        d['datetime'] = pd.to_datetime(d['datetime'], utc=True).dt.tz_localize(None)
        d = d.set_index('datetime').sort_index()
        
        # 重采样为周线
        w = d[['Open','High','Low','Close','Volume']].resample('W-FRI').agg({
            'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'
        }).dropna()
        
        if len(w) < 52:
            return None
            
        # 计算特征
        features = {}
        
        # 1. 趋势特征
        features['trend_52w'] = (w['Close'].iloc[-1] / w['Close'].iloc[-52] - 1) * 100
        features['trend_252d'] = (w['Close'].iloc[-1] / w['Close'].iloc[-min(252, len(w)-1)] - 1) * 100
        
        # 2. 波动率特征
        returns = w['Close'].pct_change().dropna()
        features['volatility_52w'] = returns.iloc[-52:].std() * np.sqrt(52) * 100
        features['volatility_all'] = returns.std() * np.sqrt(52) * 100
        
        # 3. 价格区间特征（当前价格在52周区间的位置）
        high_52w = w['High'].iloc[-52:].max()
        low_52w = w['Low'].iloc[-52:].min()
        features['price_position'] = (w['Close'].iloc[-1] - low_52w) / (high_52w - low_52w) * 100
        
        # 4. 成交量特征
        vol_ma20 = w['Volume'].rolling(20).mean()
        features['volume_trend'] = (vol_ma20.iloc[-1] / vol_ma20.iloc[-20] - 1) * 100 if pd.notna(vol_ma20.iloc[-1]) else 0
        
        # 5. 行业（从symbol推断）
        if symbol.startswith('6'):
            features['market'] = 'SH'
        elif symbol.startswith('0') or symbol.startswith('3'):
            features['market'] = 'SZ'
        else:
            features['market'] = 'Other'
            
        return features
    except Exception as e:
        return None

def main():
    # 读取周线基线结果
    result_file = "results/boll_volume_strategy_weekly_baseline/summary.csv"
    if not os.path.exists(result_file):
        print(f"结果文件不存在: {result_file}")
        return
        
    df = pd.read_csv(result_file)
    df['total_return_pct'] = pd.to_numeric(df['total_return_pct'], errors='coerce')
    df = df.dropna(subset=['total_return_pct'])
    
    # 分成赢家、输家、平庸三组
    winners = df.nlargest(10, 'total_return_pct')
    losers = df.nsmallest(10, 'total_return_pct')
    middle = df[(df['total_return_pct'] > -10) & (df['total_return_pct'] < 20)]
    
    print("=" * 80)
    print("【方案X】赢家 vs 输家特征分析")
    print("=" * 80)
    
    print("\n🏆 TOP 10 赢家:")
    print(winners[['symbol', 'total_return_pct', 'max_drawdown_pct', 'win_rate_pct', 'total_trades']].to_string(index=False))
    
    print("\n💀 BOTTOM 10 输家:")
    print(losers[['symbol', 'total_return_pct', 'max_drawdown_pct', 'win_rate_pct', 'total_trades']].to_string(index=False))
    
    # 分析特征
    print("\n" + "=" * 80)
    print("📊 特征对比分析")
    print("=" * 80)
    
    all_features = []
    for _, row in df.iterrows():
        sym = row['symbol']
        features = analyze_stock_characteristics(sym)
        if features:
            features['symbol'] = sym
            features['total_return_pct'] = row['total_return_pct']
            features['group'] = 'winner' if row['total_return_pct'] > 50 else ('loser' if row['total_return_pct'] < -20 else 'middle')
            all_features.append(features)
    
    if not all_features:
        print("无法获取股票特征数据")
        return
        
    feat_df = pd.DataFrame(all_features)
    
    # 分组统计
    print("\n【趋势特征】(52周涨幅 %)")
    print(f"  赢家平均: {feat_df[feat_df['group']=='winner']['trend_52w'].mean():.2f}%")
    print(f"  输家平均: {feat_df[feat_df['group']=='loser']['trend_52w'].mean():.2f}%")
    print(f"  平庸平均: {feat_df[feat_df['group']=='middle']['trend_52w'].mean():.2f}%")
    
    print("\n【波动率特征】(年化波动率 %)")
    print(f"  赢家平均: {feat_df[feat_df['group']=='winner']['volatility_52w'].mean():.2f}%")
    print(f"  输家平均: {feat_df[feat_df['group']=='loser']['volatility_52w'].mean():.2f}%")
    print(f"  平庸平均: {feat_df[feat_df['group']=='middle']['volatility_52w'].mean():.2f}%")
    
    print("\n【价格位置】(52周区间 %，100=新高)")
    print(f"  赢家平均: {feat_df[feat_df['group']=='winner']['price_position'].mean():.2f}%")
    print(f"  输家平均: {feat_df[feat_df['group']=='loser']['price_position'].mean():.2f}%")
    print(f"  平庸平均: {feat_df[feat_df['group']=='middle']['price_position'].mean():.2f}%")
    
    # 输出好股票画像
    print("\n" + "=" * 80)
    print("🎯 适合BOLL周线策略的'好股票'画像")
    print("=" * 80)
    
    winner_profile = feat_df[feat_df['group']=='winner']
    if len(winner_profile) > 0:
        print(f"""
1. 趋势特征:
   - 52周涨幅: {winner_profile['trend_52w'].mean():.1f}% ± {winner_profile['trend_52w'].std():.1f}%
   - 建议: 选择52周涨幅 > 30%的强势股

2. 波动率特征:
   - 年化波动: {winner_profile['volatility_52w'].mean():.1f}% ± {winner_profile['volatility_52w'].std():.1f}%
   - 建议: 选择波动率 40-60%的标的（有足够波动但不过度投机）

3. 价格位置:
   - 当前位置: {winner_profile['price_position'].mean():.1f}% ± {winner_profile['price_position'].std():.1f}%
   - 建议: 价格在52周区间的60-90%（强势但非最高点）

4. 市场分布:
   - 沪市: {(winner_profile['market']=='SH').sum()}只
   - 深市: {(winner_profile['market']=='SZ').sum()}只
        """)
    
    # 保存详细结果
    output_dir = "results/analysis"
    os.makedirs(output_dir, exist_ok=True)
    feat_df.to_csv(f"{output_dir}/winner_loser_features.csv", index=False, encoding='utf-8-sig')
    print(f"\n✅ 详细特征数据已保存: {output_dir}/winner_loser_features.csv")

if __name__ == "__main__":
    main()
