#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连续发送HTTP请求脚本 - 模拟浏览器刷新
目标URL: https://www.datadex.cn/app/buyApi?id=c77f707ad3af41cfad701fb8425b0367
"""

import requests
import time
import random
from datetime import datetime

# 配置参数
URL = "https://www.datadex.cn/app/buyApi?id=c77f707ad3af41cfad701fb8425b0367"
TOTAL_REQUESTS = 10  # 总请求次数
INTERVAL = 5  # 每次请求之间的间隔（秒）

# 模拟浏览器请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

def send_request(request_num, session, url):
    """发送单次HTTP请求"""
    try:
        start_time = time.time()
        response = session.get(url, headers=HEADERS, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"请求 #{request_num} - 状态码: {response.status_code}, "
              f"耗时: {elapsed:.2f}秒, 响应长度: {len(response.content)} bytes")
        
        return response
    except requests.exceptions.Timeout:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"请求 #{request_num} - 超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"请求 #{request_num} - 错误: {e}")
        return None

def main():
    """主函数：发送连续多次HTTP请求"""
    print(f"=" * 60)
    print(f"开始发送请求 (模拟浏览器刷新)")
    print(f"目标URL: {URL}")
    print(f"总请求次数: {TOTAL_REQUESTS}")
    print(f"请求间隔: {INTERVAL}秒")
    print(f"=" * 60)
    
    # 创建session保持连接
    session = requests.Session()
    
    for i in range(1, TOTAL_REQUESTS + 1):
        # 每次请求添加随机时间戳参数，模拟浏览器刷新
        timestamp = int(time.time() * 1000) + random.randint(1, 999)
        url_with_cache = f"{URL}&_t={timestamp}"
        
        send_request(i, session, url_with_cache)
        
        # 如果不是最后一次请求，则等待
        if i < TOTAL_REQUESTS:
            print(f"等待 {INTERVAL} 秒后发送下一次请求...")
            time.sleep(INTERVAL)
    
    print(f"=" * 60)
    print(f"所有请求已完成")
    print(f"=" * 60)

if __name__ == "__main__":
    main()
