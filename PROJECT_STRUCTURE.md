# Project Structure (Reorganized)

## Core
- core/backtest_engine.py

## Data
- data/data_fetcher.py
- data/fetch_china_futures.py
- data/create_cache.py

## Indicators
- indicators/chan/*
- indicators/boll/*

## Visualization
- visualization/kline_plotter.py
- visualization/interactive_kline.py
- visualization/kline_tool.py
- visualization/plot_*.py

## Backtests
- backtests/backtest_*.py

## Analysis
- analysis/analyze_*.py
- analysis/compare_*.py
- analysis/summarize_results.py
- analysis/verify_backtest.py

## Scanners
- scanners/scan_*.py

## Debug
- debug_tools/debug_*.py
- debug_tools/fix_*.py

## Tests
- tests/test_*.py

## Examples
- examples/example_*.py

## Scripts
- scripts/main.py
- scripts/quick_test.py
- scripts/add_output.py
- scripts/update_signals.py

## Compatibility
Root-level legacy file names are preserved as compatibility shims. Existing commands like
`python backtest_futures_minute.py` still work and delegate to new module locations.
