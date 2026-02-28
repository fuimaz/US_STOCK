@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo A股分钟数据定时增量更新
echo 每天 17:10 更新 5/15/30/60 分钟前复权数据
echo 按 Ctrl+C 可退出
echo ========================================

python data\update_a_stock_minute.py --daemon --run-time 17:10 --adjust qfq

pause
