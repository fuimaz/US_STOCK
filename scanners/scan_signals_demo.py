"""
缠论买卖点信号扫描 - 演示版本（带示例输出）
展示当有信号时的输出格式
"""
from datetime import datetime


def print_demo_output():
    """打印演示输出"""
    
    print("=" * 100)
    print(f"Chan Theory Real-time Signal Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)
    print("Stock universe: 67 stocks")
    print()
    
    # 模拟扫描过程
    demo_stocks = [
        ("000001.SZ", "平安银行", None),
        ("000333.SZ", "美的集团", "buy"),
        ("600519.SS", "贵州茅台", None),
        ("002594.SZ", "比亚迪", "sell"),
        ("601012.SS", "隆基绿能", "both"),
    ]
    
    for i, (symbol, name, signal_type) in enumerate(demo_stocks, 1):
        print(f"[{i}/{len(demo_stocks)}] Scanning: {name} ({symbol})")
        
        if signal_type is None:
            print(f"  No recent signals")
        elif signal_type == "buy":
            print(f"  >>> BUY SIGNAL: Type 1 Buy @ 77.85 (+1.73%)")
        elif signal_type == "sell":
            print(f"  >>> SELL SIGNAL: Type 1 Sell @ 285.50 (+3.20%)")
        elif signal_type == "both":
            print(f"  >>> BUY SIGNAL: Type 2 Buy @ 25.60 (+0.85%)")
            print(f"  >>> SELL SIGNAL: Type 1 Sell @ 28.90 (+5.60%)")
        print()
    
    print("=" * 100)
    print("Scan complete")
    print(f"  Buy signals: 2")
    print(f"  Sell signals: 2")
    print(f"  Errors: 0")
    print("=" * 100)
    
    # 买点汇总
    print("\n" + "=" * 100)
    print("SIGNAL SUMMARY")
    print("=" * 100)
    
    print(f"\n[ BUY SIGNALS ] - Total: 2")
    print(f"{'Symbol':<12} {'Name':<10} {'Date':<12} {'Type':<14} {'SigPrice':<10} {'CurPrice':<10} {'Change':<8}")
    print("-" * 90)
    print(f"{'000333.SZ':<12} {'美的集团':<10} {'2026-02-20':<12} {'Type 1 Buy':<14} {77.85:>8.2f} {79.20:>8.2f} {+1.73:>+6.2f}%")
    print(f"{'601012.SS':<12} {'隆基绿能':<10} {'2026-02-21':<12} {'Type 2 Buy':<14} {25.60:>8.2f} {25.82:>8.2f} {+0.85:>+6.2f}%")
    
    print(f"\n[ SELL SIGNALS ] - Total: 2")
    print(f"{'Symbol':<12} {'Name':<10} {'Date':<12} {'Type':<14} {'SigPrice':<10} {'CurPrice':<10} {'Change':<8}")
    print("-" * 90)
    print(f"{'002594.SZ':<12} {'比亚迪':<10} {'2026-02-20':<12} {'Type 1 Sell':<14} {285.50:>8.2f} {294.64:>8.2f} {+3.20:>+6.2f}%")
    print(f"{'601012.SS':<12} {'隆基绿能':<10} {'2026-02-19':<12} {'Type 1 Sell':<14} {28.90:>8.2f} {30.52:>8.2f} {+5.60:>+6.2f}%")
    
    print("\n" + "=" * 100)
    
    print("\n" + "=" * 100)
    print("SIGNAL TYPE EXPLANATION")
    print("=" * 100)
    print("""
【买点信号】
- Type 1 Buy (第一类买点): 下跌线段结束，向上突破中枢，趋势反转信号
- Type 2 Buy (第二类买点): 第一类买点后回调不创新低，确认上涨

【卖点信号】
- Type 1 Sell (第一类卖点): 上涨线段结束，向下跌破中枢，趋势反转信号  
- Type 2 Sell (第二类卖点): 第一类卖点后反弹不创新高，确认下跌

【操作建议】
- 买点信号: 考虑建仓或加仓
- 卖点信号: 考虑减仓或清仓
- 同时出现买卖信号: 可能处于震荡区间，观望或高抛低吸
    """)
    print("=" * 100)
    
    print("\n" + "=" * 100)
    print("RESULTS SAVED")
    print("=" * 100)
    print("Results saved to: results/realtime_scan/")
    print("  - buy_signals_YYYYMMDD_HHMMSS.csv")
    print("  - sell_signals_YYYYMMDD_HHMMSS.csv")
    print("  - summary_YYYYMMDD_HHMMSS.json")
    print("=" * 100)


if __name__ == '__main__':
    print_demo_output()
