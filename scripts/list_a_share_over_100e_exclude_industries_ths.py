"""
List A-share stocks with market cap above a threshold, excluding some industries.

Data source:
  - TongHuaShun (同花顺) industry pages: http://q.10jqka.com.cn/thshy/

Market cap field:
  - Uses "流通市值" from THS pages (unit: 亿元)

Example:
  python scripts/list_a_share_over_100e_exclude_industries_ths.py --threshold-yi 100
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd
import py_mini_racer
import requests
from bs4 import BeautifulSoup

import akshare as ak
from akshare.datasets import get_ths_js


@dataclass(frozen=True)
class StockRow:
    code: str
    name: str
    industry: str
    float_mv_yi: float


def _now_cn_str() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")


def _mk_session(v_cookie: str) -> requests.Session:
    s = requests.Session()
    s.trust_env = False  # avoid system proxies
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Cookie": f"v={v_cookie}",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "close",
        }
    )
    return s


def _get_v_cookie() -> str:
    js_path = get_ths_js("ths.js")
    js_content = Path(js_path).read_text(encoding="utf-8")
    ctx = py_mini_racer.MiniRacer()
    ctx.eval(js_content)
    return str(ctx.call("v"))


def _parse_yi_number(text: str) -> Optional[float]:
    """
    Parse a number that may include unit suffix:
      - "18026.70亿" -> 18026.70
      - "123.45万" -> 0.012345 (in 亿)
      - "—" / "" -> None
    Returns value in 亿元.
    """
    if text is None:
        return None
    s = str(text).strip()
    if not s or s in {"-", "—", "--", "None", "nan"}:
        return None
    s = s.replace(",", "")
    m = re.match(r"^(-?\d+(?:\.\d+)?)([亿万]?)$", s)
    if not m:
        # try to extract numeric part
        m2 = re.search(r"(-?\d+(?:\.\d+)?)", s)
        if not m2:
            return None
        return float(m2.group(1))
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "亿" or unit == "":
        return val
    if unit == "万":
        return val / 10000.0
    return val


def _page_url(industry_code: str, page: int) -> str:
    base = f"http://q.10jqka.com.cn/thshy/detail/code/{industry_code}/"
    if page <= 1:
        return base
    return f"{base}page/{page}/"


def _get_page_count(soup: BeautifulSoup) -> int:
    info = soup.select_one(".page_info")
    if not info:
        return 1
    t = info.get_text(strip=True)  # like "1/9"
    m = re.match(r"^\d+/(\\d+)$", t)
    if not m:
        return 1
    return int(m.group(1))


def _parse_table_rows(
    soup: BeautifulSoup, industry_name: str
) -> List[StockRow]:
    table = soup.find("table")
    if not table:
        return []
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    idx_code = headers.index("代码") if "代码" in headers else None
    idx_name = headers.index("名称") if "名称" in headers else None
    idx_mv = headers.index("流通市值") if "流通市值" in headers else None
    if idx_code is None or idx_name is None or idx_mv is None:
        return []

    out: List[StockRow] = []
    for tr in table.find_all("tr")[1:]:
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not tds or len(tds) <= max(idx_code, idx_name, idx_mv):
            continue
        code = str(tds[idx_code]).strip().zfill(6)
        name = str(tds[idx_name]).strip()
        mv_yi = _parse_yi_number(tds[idx_mv])
        if not code or not code.isdigit() or mv_yi is None:
            continue
        out.append(StockRow(code=code, name=name, industry=industry_name, float_mv_yi=float(mv_yi)))
    return out


def _guess_exchange_suffix(code6: str) -> str:
    if code6.startswith(("5", "6", "9")):
        return "SS"
    if code6.startswith(("0", "3")):
        return "SZ"
    if code6.startswith(("8", "4")):
        # Beijing Stock Exchange commonly starts with 8; some legacy codes can start with 4
        return "BJ"
    return ""


def fetch_industry_constituents(
    industry_code: str,
    industry_name: str,
    session: requests.Session,
    sleep_sec: float = 0.1,
    max_pages: Optional[int] = None,
) -> List[StockRow]:
    url1 = _page_url(industry_code, 1)
    r1 = session.get(url1, timeout=25)
    r1.raise_for_status()
    soup1 = BeautifulSoup(r1.text, "lxml")
    total_pages = _get_page_count(soup1)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    rows: List[StockRow] = []
    rows.extend(_parse_table_rows(soup1, industry_name))

    for page in range(2, total_pages + 1):
        time.sleep(sleep_sec)
        url = _page_url(industry_code, page)
        rp = session.get(url, timeout=25)
        rp.raise_for_status()
        soup = BeautifulSoup(rp.text, "lxml")
        rows.extend(_parse_table_rows(soup, industry_name))
    return rows


def build_list(
    threshold_yi: float,
    excluded_industries: Iterable[str],
    sleep_sec: float = 0.1,
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    excluded = set(excluded_industries)
    industry_df = ak.stock_board_industry_name_ths()
    # columns: name, code
    industries = [(str(r["code"]), str(r["name"])) for _, r in industry_df.iterrows()]

    v_cookie = _get_v_cookie()
    session = _mk_session(v_cookie=v_cookie)

    kept_rows: List[StockRow] = []
    stats = {"industries_total": len(industries), "industries_skipped": 0, "pages_errors": 0}

    for code, name in industries:
        if name in excluded:
            stats["industries_skipped"] += 1
            continue
        try:
            rows = fetch_industry_constituents(
                industry_code=code,
                industry_name=name,
                session=session,
                sleep_sec=sleep_sec,
            )
            for row in rows:
                if row.float_mv_yi >= threshold_yi:
                    kept_rows.append(row)
        except Exception:
            stats["pages_errors"] += 1
            continue

    if not kept_rows:
        return pd.DataFrame(), stats

    df = pd.DataFrame(
        [
            {
                "code": r.code,
                "exchange": _guess_exchange_suffix(r.code),
                "symbol": f"{r.code}.{_guess_exchange_suffix(r.code)}" if _guess_exchange_suffix(r.code) else r.code,
                "name": r.name,
                "industry_ths": r.industry,
                "float_mv_yi": r.float_mv_yi,
                "asof": _now_cn_str(),
                "mv_threshold_yi": float(threshold_yi),
            }
            for r in kept_rows
        ]
    )

    # In THS industries, a stock should map to one industry; still dedupe defensively.
    df.sort_values(["float_mv_yi"], ascending=False, inplace=True)
    df = df.drop_duplicates(subset=["code"], keep="first").reset_index(drop=True)
    return df, stats


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--threshold-yi", type=float, default=100.0, help="Threshold in 亿元; default 100.")
    p.add_argument(
        "--exclude",
        nargs="*",
        default=["白酒", "房地产", "建筑材料", "建筑装饰"],
        help="THS industry names to exclude (exact match).",
    )
    p.add_argument("--sleep-sec", type=float, default=0.1, help="Sleep between page requests.")
    p.add_argument("--out-dir", type=str, default="results", help="Output directory.")
    args = p.parse_args()

    df, stats = build_list(
        threshold_yi=float(args.threshold_yi),
        excluded_industries=args.exclude,
        sleep_sec=float(args.sleep_sec),
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"a_share_float_mv_ge_{int(args.threshold_yi)}yi_excl_{stamp}.csv"
    txt_path = out_dir / f"a_share_codes_float_mv_ge_{int(args.threshold_yi)}yi_excl_{stamp}.txt"

    if df.empty:
        print("No data collected. Stats:", stats)
        return 2

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df["symbol"].to_csv(txt_path, index=False, header=False, encoding="utf-8")

    print(f"[OK] Saved: {csv_path}")
    print(f"[OK] Saved: {txt_path}")
    print(f"count={len(df)} | threshold_yi={args.threshold_yi} | excluded={args.exclude}")
    print("stats:", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

