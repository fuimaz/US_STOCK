#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量发送HTTP请求脚本 - 使用Selenium模拟真实浏览器刷新（多线程版本）
目标URL: 多个datadex页面，每个URL一个线程

使用方法:
1. 确保已安装Chrome浏览器
2. 安装selenium: pip install selenium
3. 运行脚本: python scripts/send_requests_multi.py
"""

import time
import random
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 配置参数 - 多个URL
URLS = [
    # "https://www.datadex.cn/app/buyApi?id=1afa912d991344599eedc78cc255b913",
    # "https://www.datadex.cn/app/buyApi?id=629cdebe031f423a973e25e83ad9d66e",
    "https://www.datadex.cn/app/buyApi?id=c77f707ad3af41cfad701fb8425b0367",
    # "https://www.datadex.cn/app/buyApi?id=2fdd438c91224fca9083f457a8ca943f",
    # "https://www.datadex.cn/app/buyApi?id=7d763312c47a456095cf95a2c005b2b7",
    # "https://www.datadex.cn/app/buyApi?id=50503ff3adb946e9bc8b3727c7eaac0b",
    # "https://www.datadex.cn/app/buyApi?id=761951a697a74eee92476453e38d0643",
    # "https://www.datadex.cn/app/buyApi?id=3ac55077c98145768614452f91de151f",
    # "https://www.datadex.cn/app/buyApi?id=68d631135f714cb884ca47fc0a0f7deb",
]

# 每个URL的请求次数范围（随机）
MIN_REQUESTS = 10
MAX_REQUESTS = 60

# 每次请求之间的间隔（秒）
INTERVAL = 3

# 是否使用无头模式（不显示浏览器窗口）
HEADLESS = True

# 全局计数器
completed_counts = {}
lock = threading.Lock()

def setup_driver(headless=True):
    """设置Chrome浏览器选项"""
    options = Options()
    if headless:
        options.add_argument('--headless')
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

def refresh_page(driver, url_index, request_num):
    """刷新页面"""
    try:
        start_time = time.time()
        
        # 刷新页面 - 使用driver.refresh()模拟浏览器刷新
        driver.refresh()
        
        # 等待页面加载，随机延迟模拟真实用户
        time.sleep(random.uniform(1, 2))
        
        elapsed = time.time() - start_time
        
        # 获取页面长度
        page_length = len(driver.page_source)
        
        # 更新计数器
        with lock:
            completed_counts[url_index] = completed_counts.get(url_index, 0) + 1
            count = completed_counts[url_index]
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"URL{url_index+1} #{count} - "
              f"耗时:{elapsed:.1f}秒")
        
        return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"URL{url_index+1} 错误: {e}")
        return False

def process_url(url_index, url, request_count, stop_event):
    """处理单个URL的请求"""
    driver = None
    try:
        print(f"[Thread {url_index+1}] 初始化浏览器...")
        driver = setup_driver(HEADLESS)
        
        # 首次访问页面
        driver.get(url)
        time.sleep(random.uniform(2, 3))
        print(f"[Thread {url_index+1}] 开始刷新...")
        
        # 循环刷新直到达到请求次数或收到停止信号
        while not stop_event.is_set():
            with lock:
                current_count = completed_counts.get(url_index, 0)
            
            if current_count >= request_count:
                break
            
            if refresh_page(driver, url_index, current_count + 1):
                time.sleep(INTERVAL)
            else:
                time.sleep(INTERVAL)
        
        with lock:
            final_count = completed_counts.get(url_index, 0)
        
        print(f"[Thread {url_index+1}] 完成: {final_count}/{request_count} 次请求")
        
    except Exception as e:
        print(f"[Thread {url_index+1}] 错误: {e}")
    finally:
        if driver:
            driver.quit()

def main():
    """主函数：使用多线程同时处理多个URL"""
    print(f"{'='*60}")
    print(f"批量发送请求 (多线程版本 - 同时运行 {len(URLS)} 个线程)")
    print(f"{'='*60}")
    print(f"URL数量: {len(URLS)}")
    print(f"每个URL请求次数: {MIN_REQUESTS}-{MAX_REQUESTS} (随机)")
    print(f"请求间隔: {INTERVAL}秒")
    print(f"无头模式: {HEADLESS}")
    print(f"{'='*60}")
    
    # 为每个URL生成随机请求次数
    requests_per_url = {}
    total_requests = 0
    for i, url in enumerate(URLS):
        count = random.randint(MIN_REQUESTS, MAX_REQUESTS)
        requests_per_url[i] = count
        total_requests += count
        print(f"URL {i+1}: {count} 次请求")
        completed_counts[i] = 0
    
    print(f"\n总请求次数: {total_requests}")
    print(f"预计耗时: 约 {total_requests * INTERVAL / 60 / len(URLS):.0f} 分钟")
    print(f"{'='*60}")
    
    # 创建停止事件
    stop_event = threading.Event()
    
    # 创建并启动线程
    threads = []
    for i, url in enumerate(URLS):
        t = threading.Thread(target=process_url, args=(i, url, requests_per_url[i], stop_event))
        threads.append(t)
        t.start()
        print(f"[Main] 启动线程 {i+1}/{len(URLS)}")
    
    print(f"\n所有线程已启动，等待完成...")
    
    try:
        # 等待所有线程完成
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\n用户中断，停止所有线程...")
        stop_event.set()
        # 等待线程结束
        for t in threads:
            t.join(timeout=5)
    
    # 打印最终统计
    print(f"\n{'='*60}")
    print("所有请求已完成！")
    print("统计:")
    for i in range(len(URLS)):
        print(f"  URL {i+1}: {completed_counts.get(i, 0)} 次请求")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
