"""
方案Y：动态选股过滤器
只交易趋势最强的前N%股票，定期轮换
"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.boll.boll_volume_strategy import BollVolumeStrategy
from backtests.backtest_boll_volume_strategy import run_backtest, load_stock_data


class DynamicStockSelector:
    """动态选股器：根据趋势强度定期筛选股票"""
    
    def __init__(self, top_percentile=0.2, min_stocks=5, rebalance_weeks=4):
        """
        Args:
            top_percentile: 选择前多少百分比的股票（0.2=前20%）
            min_stocks: 最少选几只
            rebalance_weeks: 多少周重新平衡一次
        """
        self.top_percentile = top_percentile
        self.min_stocks = min_stocks
        self.rebalance_weeks = rebalance_weeks
        
    def calculate_trend_score(self, data, date):
        """计算单只股票的趋势得分（越高越强）"""
        try:
            # 只用date之前的数据
            hist = data[data.index <= date]
            if len(hist) < 52:
                return None
                
            w = hist[['Close', 'Volume']].resample('W-FRI').last().dropna()
            if len(w) < 52:
                return None
            
            scores = {}
            
            # 1. 52周涨幅（最重要）
            scores['return_52w'] = (w['Close'].iloc[-1] / w['Close'].iloc[-52] - 1) * 100
            
            # 2. 20周涨幅（近期强势）
            scores['return_20w'] = (w['Close'].iloc[-1] / w['Close'].iloc[-20] - 1) * 100
            
            # 3. 趋势一致性（周收阳线比例）
            weekly_returns = w['Close'].pct_change().dropna()
            scores['consistency'] = (weekly_returns.iloc[-20:] > 0).mean() * 100
            
            # 4. 波动率调整收益（夏普-like）
            volatility = weekly_returns.iloc[-20:].std() * np.sqrt(52) * 100
            scores['risk_adj_return'] = scores['return_20w'] / (volatility + 1e-6)
            
            # 5. 成交量趋势
            vol_ma5 = w['Volume'].rolling(5).mean().iloc[-1]
            vol_ma20 = w['Volume'].rolling(20).mean().iloc[-1]
            scores['volume_trend'] = (vol_ma5 / vol_ma20 - 1) * 100 if vol_ma20 > 0 else 0
            
            # 综合得分（可调整权重）
            total_score = (
                scores['return_52w'] * 0.4 +      # 40%权重给长期趋势
                scores['return_20w'] * 0.3 +      # 30%权重给短期趋势
                scores['consistency'] * 0.1 +     # 10%权重给一致性
                scores['risk_adj_return'] * 10 +  # 10%权重给风险调整收益
                scores['volume_trend'] * 0.1      # 10%权重给量能
            )
            
            return {
                'total_score': total_score,
                'details': scores
            }
        except Exception as e:
            return None
    
    def select_stocks(self, all_symbols, date, data_cache):
        """在指定日期选出最强的股票"""
        scores = []
        
        for sym in all_symbols:
            if sym not in data_cache:
                continue
            result = self.calculate_trend_score(data_cache[sym], date)
            if result:
                scores.append({
                    'symbol': sym,
                    'score': result['total_score'],
                    'details': result['details']
                })
        
        if not scores:
            return []
            
        # 按得分排序
        scores_df = pd.DataFrame(scores)
        scores_df = scores_df.sort_values('score', ascending=False)
        
        # 取前N%
        n_select = max(self.min_stocks, int(len(scores_df) * self.top_percentile))
        selected = scores_df.head(n_select)
        
        return selected['symbol'].tolist()


def run_dynamic_backtest(
    symbols,
    start_date,
    end_date,
    selector,
    strategy,
    initial_capital=100000.0
):
    """
    运行动态选股回测
    定期重新平衡股票池，只在选中的股票上运行BOLL策略
    """
    # 预加载所有数据
    print("预加载股票数据...")
    data_cache = {}
    for sym in symbols:
        data = load_stock_data(sym)
        if data is not None and len(data) >= 120:
            data_cache[sym] = data
    
    print(f"成功加载 {len(data_cache)} 只股票")
    
    # 生成再平衡日期（每4周）
    rebalance_dates = pd.date_range(start=start_date, end=end_date, freq=f'{selector.rebalance_weeks}W')
    
    all_results = []
    portfolio_history = []
    
    for i, rebalance_date in enumerate(rebalance_dates):
        print(f"\n{'='*60}")
        print(f"再平衡 #{i+1}: {rebalance_date.strftime('%Y-%m-%d')}")
        
        # 选股
        selected_symbols = selector.select_stocks(list(data_cache.keys()), rebalance_date, data_cache)
        print(f"选中 {len(selected_symbols)} 只股票: {selected_symbols[:5]}...")
        
        # 计算持仓期（到下次再平衡或结束）
        hold_end = rebalance_dates[i+1] if i+1 < len(rebalance_dates) else end_date
        
        # 对每只选中的股票运行策略
        period_returns = []
        for sym in selected_symbols:
            try:
                data = data_cache[sym]
                # 提取持仓期数据
                mask = (data.index >= rebalance_date) & (data.index <= hold_end)
                period_data = data[mask].copy()
                
                if len(period_data) < 10:
                    continue
                    
                # 运行BOLL策略
                result = run_backtest(
                    period_data,
                    strategy,
                    initial_capital=initial_capital / len(selected_symbols),  # 等权分配
                    use_dynamic_stop=False,  # 用基线策略
                    use_partial_take_profit=False
                )
                
                period_returns.append({
                    'symbol': sym,
                    'return_pct': result['total_return_pct'],
                    'period': f"{rebalance_date.strftime('%Y%m%d')}-{hold_end.strftime('%Y%m%d')}"
                })
                
            except Exception as e:
                print(f"  {sym} 回测失败: {e}")
                continue
        
        if period_returns:
            avg_return = np.mean([r['return_pct'] for r in period_returns])
            print(f"本期平均收益: {avg_return:.2f}%")
            portfolio_history.append({
                'date': rebalance_date,
                'symbols': selected_symbols,
                'avg_return': avg_return,
                'details': period_returns
            })
    
    return portfolio_history


def main():
    print("=" * 80)
    print("【方案Y】动态选股回测")
    print("=" * 80)
    
    # 1. 获取所有股票
    cache_dir = "data_cache"
    suffix = "_20y_1d_forward.csv"
    symbols = []
    for f in os.listdir(cache_dir):
        if f.endswith(suffix):
            sym = f[:-len(suffix)]
            if sym.endswith(('.SZ', '.SS', '.SH')):
                symbols.append(sym)
    
    print(f"发现 {len(symbols)} 只A股")
    
    # 2. 创建选股器
    selector = DynamicStockSelector(
        top_percentile=0.2,    # 前20%
        min_stocks=5,          # 最少5只
        rebalance_weeks=4      # 每月再平衡
    )
    
    # 3. 设置回测时间
    end_date = pd.Timestamp('2026-02-13')
    start_date = end_date - timedelta(days=5*365)  # 5年
    
    # 4. 创建策略
    strategy = BollVolumeStrategy()
    
    # 5. 运行动态回测
    print(f"\n回测区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    print(f"选股规则: 每{selector.rebalance_weeks}周选取趋势最强的前{int(selector.top_percentile*100)}%")
    
    history = run_dynamic_backtest(
        symbols,
        start_date,
        end_date,
        selector,
        strategy
    )
    
    # 6. 统计结果
    print("\n" + "=" * 80)
    print("📊 动态选股组合表现")
    print("=" * 80)
    
    if history:
        avg_returns = [h['avg_return'] for h in history]
        print(f"再平衡次数: {len(history)}")
        print(f"平均每期收益: {np.mean(avg_returns):.2f}%")
        print(f"收益中位数: {np.median(avg_returns):.2f}%")
        print(f"最好一期: {max(avg_returns):.2f}%")
        print(f"最差一期: {min(avg_returns):.2f}%")
        print(f"正收益期数: {(np.array(avg_returns) > 0).sum()}/{len(avg_returns)}")
        
        # 累计收益（简化计算，假设等权再平衡）
        cumulative = 1.0
        for ret in avg_returns:
            cumulative *= (1 + ret/100)
        total_return = (cumulative - 1) * 100
        annualized = ((cumulative) ** (1/5) - 1) * 100  # 5年
        
        print(f"\n累计收益: {total_return:.2f}%")
        print(f"年化收益: {annualized:.2f}%")
        
        # 保存结果
        output_dir = "results/analysis"
        os.makedirs(output_dir, exist_ok=True)
        
        history_df = pd.DataFrame([
            {
                'date': h['date'],
                'num_stocks': len(h['symbols']),
                'symbols': ','.join(h['symbols']),
                'avg_return': h['avg_return']
            }
            for h in history
        ])
        history_df.to_csv(f"{output_dir}/dynamic_selector_history.csv", index=False, encoding='utf-8-sig')
        print(f"\n✅ 详细结果已保存: {output_dir}/dynamic_selector_history.csv")

if __name__ == "__main__":
    main()
