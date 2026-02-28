#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试不同的请求方式，模拟浏览器刷新
"""

import requests
import time
from datetime import datetime

# 目标URL
URL = "https://www.datadex.cn/app/buyApi?id=c77f707ad3af41cfad701fb8425b0367"

# 模拟真实浏览器的请求头
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

# 禁用SSL警告
import urllib3
urllib3.disable_warnings()

def test_request():
    """测试请求"""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    print("开始连续请求测试...")
    print("=" * 60)
    
    for i in range(5):
        response = session.get(URL, verify=False, timeout=30)
        
        # 尝试不同编码
        try:
            # 先尝试使用response的编码
            content = response.text
        except:
            content = response.content.decode('utf-8', errors='ignore')
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"请求 #{i+1}: 状态码={response.status_code}, "
              f"内容长度={len(response.content)}, "
              f"编码={response.encoding}")
        
        # 打印部分内容（去掉HTML标签看看有没有特殊内容）
        import re
        text_only = re.sub(r'<[^>]+>', '', content)
        text_only = text_only.strip()
        print(f"  文本内容: {text_only[:200]}...")
        
        if i < 4:
            print(f"  等待5秒...")
            time.sleep(5)
    
    print("=" * 60)
    print("测试完成")

if __name__ == "__main__":
    test_request()
