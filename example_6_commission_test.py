from data_fetcher import DataFetcher
from backtest_engine import BacktestEngine
from strategies import MovingAverageStrategy

print("=" * 60)
print("示例：不同手续费下的策略表现")
print("=" * 60)

# 获取数据
fetcher = DataFetcher()
print("\n正在获取AAPL数据...")
data = fetcher.fetch_stock_data('AAPL', period='2y')
print(f"✓ 获取到 {len(data)} 条数据")

# 不同的手续费设置
commissions = [0.000, 0.001, 0.003, 0.005, 0.010]

print(f"\n正在测试 {len(commissions)} 种手续费设置...")
print("-" * 70)
print(f"{'手续费率':<12} {'最终资金':<18} {'收益率':<12} {'夏普比率':<10} {'交易次数':<8}")
print("-" * 70)

results_list = []
for comm in commissions:
    engine = BacktestEngine(initial_capital=100000, commission=comm)
    strategy = MovingAverageStrategy(short_period=5, long_period=20)
    results = engine.run_backtest(data, strategy)
    results_list.append(results)
    
    print(f"{comm*100:>8.3f}% "
          f"${results['final_capital']:>14,.2f} "
          f"{results['total_return_pct']:>8.2f}% "
          f"{results['sharpe_ratio']:>8.2f} "
          f"{results['total_trades']:>6}")

print("-" * 70)

# 分析结果
print("\n分析结果:")
print("-" * 70)
best_result = max(results_list, key=lambda x: x['total_return_pct'])
worst_result = min(results_list, key=lambda x: x['total_return_pct'])

print(f"最佳表现 (手续费 {best_result['total_trades'] * 0.001 * 100:.3f}%): "
      f"收益率 {best_result['total_return_pct']:.2f}%")
print(f"最差表现 (手续费 {worst_result['total_trades'] * 0.001 * 100:.3f}%): "
      f"收益率 {worst_result['total_return_pct']:.2f}%")

# 计算手续费影响
commission_impact = best_result['total_return_pct'] - worst_result['total_return_pct']
print(f"\n手续费影响: {commission_impact:.2f}%")

print("\n✓ 完成！")
