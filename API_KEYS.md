# API密钥配置说明

本项目支持多个数据源来获取真实的股票数据。当主要数据源（yfinance）不可用时，会自动尝试其他数据源。

## 支持的数据源

### 1. yfinance（默认，无需API密钥）
- 免费使用
- 有请求频率限制
- 优先使用此数据源

### 2. Alpha Vantage
- 免费API密钥：https://www.alphavantage.co/support/#api-key
- 每天免费请求：25次
- 设置方法：
  ```bash
  # Windows
  set ALPHA_VANTAGE_API_KEY=your_api_key_here
  
  # Linux/Mac
  export ALPHA_VANTAGE_API_KEY=your_api_key_here
  ```

### 3. Polygon.io
- 免费API密钥：https://polygon.io/
- 每分钟免费请求：5次
- 设置方法：
  ```bash
  # Windows
  set POLYGON_API_KEY=your_api_key_here
  
  # Linux/Mac
  export POLYGON_API_KEY=your_api_key_here
  ```

### 4. Twelve Data
- 免费API密钥：https://twelvedata.com/
- 每天免费请求：800次
- 设置方法：
  ```bash
  # Windows
  set TWELVE_DATA_API_KEY=your_api_key_here
  
  # Linux/Mac
  export TWELVE_DATA_API_KEY=your_api_key_here
  ```

## 推荐配置

为了获得最佳体验，建议至少配置一个备用数据源的API密钥：

1. **免费方案**：注册 Twelve Data（每天800次免费请求）
2. **稳定方案**：注册 Alpha Vantage + Twelve Data
3. **专业方案**：所有数据源都配置

## 使用方法

设置环境变量后，直接运行程序即可：

```bash
python interactive_kline.py -s AAPL -t 1d
```

程序会自动尝试各个数据源，直到成功获取数据。

## 注意事项

- 所有API密钥都是免费的
- 请妥善保管您的API密钥
- 不要将API密钥提交到版本控制系统
- 每个数据源都有不同的请求限制，请合理使用