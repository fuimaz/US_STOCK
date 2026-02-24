from data_fetcher import DataFetcher

print("=" * 60)
print("示例：获取股票基本信息")
print("=" * 60)

# 初始化
fetcher = DataFetcher()

# 获取多只股票信息
symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']

print(f"\n正在获取 {len(symbols)} 只股票的基本信息...\n")

for symbol in symbols:
    print(f"{'='*60}")
    info = fetcher.get_stock_info(symbol)
    
    print(f"股票代码: {symbol}")
    print(f"公司名称: {info['name']}")
    print(f"行业: {info['industry']}")
    print(f"板块: {info['sector']}")
    
    # 格式化市值
    market_cap = info['market_cap']
    if market_cap >= 1e12:
        market_cap_str = f"${market_cap/1e12:.2f}万亿"
    elif market_cap >= 1e9:
        market_cap_str = f"${market_cap/1e9:.2f}亿"
    else:
        market_cap_str = f"${market_cap:,.0f}"
    
    print(f"市值: {market_cap_str}")
    print(f"当前价格: ${info['current_price']:.2f}")
    print(f"前收盘价: ${info['previous_close']:.2f}")
    
    # 计算涨跌
    if info['previous_close'] > 0:
        change_pct = ((info['current_price'] / info['previous_close']) - 1) * 100
        if change_pct >= 0:
            print(f"涨跌: +{change_pct:.2f}%")
        else:
            print(f"涨跌: {change_pct:.2f}%")
    
    print()

print("✓ 完成！")
