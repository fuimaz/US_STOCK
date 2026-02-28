#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连续发送HTTP请求脚本 - 使用Selenium模拟真实浏览器刷新
目标URL: https://www.datadex.cn/app/buyApi?id=c77f707ad3af41cfad701fb8425b0367

使用方法:
1. 确保已安装Chrome浏览器
2. 安装selenium: pip install selenium
3. 运行脚本: python scripts/send_requests_browser.py
"""

import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 配置参数
URL = "https://www.datadex.cn/app/buyApi?id=c77f707ad3af41cfad701fb8425b0367"
TOTAL_REQUESTS = 3152  # 总请求次数
INTERVAL = 1  # 每次请求之间的间隔（秒）

def setup_driver():
    """设置Chrome浏览器选项"""
    options = Options()
    # options.add_argument('--headless')  # 注释掉无头模式，方便查看浏览器操作
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 模拟真实浏览器
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    # 隐藏webdriver标识
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver

def refresh_page(driver, request_num):
    """刷新页面"""
    try:
        start_time = time.time()
        
        # 刷新页面 - 使用driver.refresh()模拟浏览器刷新
        driver.refresh()
        
        # 等待页面加载，随机延迟模拟真实用户
        time.sleep(random.uniform(2, 4))
        
        elapsed = time.time() - start_time
        
        # 获取页面信息
        title = driver.title
        page_length = len(driver.page_source)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"请求 #{request_num} - 刷新成功, "
              f"耗时: {elapsed:.2f}秒, "
              f"页面长度: {page_length}, "
              f"标题: {title[:30]}...")
        
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"请求 #{request_num} - 错误: {e}")
        return False

def main():
    """主函数：使用Selenium连续刷新页面"""
    print(f"=" * 60)
    print(f"开始发送请求 (使用Selenium模拟浏览器刷新)")
    print(f"目标URL: {URL}")
    print(f"总请求次数: {TOTAL_REQUESTS}")
    print(f"请求间隔: {INTERVAL}秒")
    print(f"=" * 60)
    
    driver = None
    try:
        # 初始化浏览器
        print("初始化Chrome浏览器...")
        driver = setup_driver()
        
        # 首次访问页面
        print("首次访问页面...")
        driver.get(URL)
        time.sleep(random.uniform(3, 5))  # 等待页面加载
        print(f"页面加载完成: {driver.title[:30]}...")
        
        # 开始循环刷新
        for i in range(1, TOTAL_REQUESTS + 1):
            refresh_page(driver, i)
            
            # 如果不是最后一次请求，则等待
            if i < TOTAL_REQUESTS:
                print(f"等待 {INTERVAL} 秒后发送下一次请求...")
                time.sleep(INTERVAL)
        
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if driver:
            print("关闭浏览器...")
            driver.quit()
    
    print(f"=" * 60)
    print(f"所有请求已完成")
    print(f"=" * 60)

if __name__ == "__main__":
    main()
