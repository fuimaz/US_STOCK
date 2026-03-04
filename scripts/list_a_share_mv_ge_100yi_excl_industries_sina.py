"""
List A-share stocks with market cap >= threshold, excluding specific industries.

Data source:
  - Sina Market Center (新浪行情中心) node data:
    http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData

Market cap field:
  - Uses response field "mktcap" (total market cap) in 万元.
  - Converts to 亿元 via: total_mv_yi = mktcap / 10000

Industry exclusion:
  - Uses Sina "行业" nodes (labels like hangye_ZK70).
  - Fetches constituents for excluded nodes and removes them from the final list.

Example:
  python scripts/list_a_share_mv_ge_100yi_excl_industries_sina.py --threshold-yi 100
"""

from __future__ import annotations

import argparse
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd
import requests

import akshare as ak
from akshare.stock.cons import zh_sina_a_stock_payload, zh_sina_a_stock_url
from akshare.utils import demjson


DEFAULT_EXCLUDE_INDUSTRY_NODES = [
    # 酒（包含酒、饮料、精制茶制造业）
    "hangye_ZC15",
    # 房地产
    "hangye_ZK70",
    # 基建/建筑相关
    "hangye_ZE47",  # 房屋建筑业
    "hangye_ZE48",  # 土木工程建筑业
    "hangye_ZE49",  # 建筑安装业
    "hangye_ZE50",  # 建筑装饰和其他建筑业
]


def _now_str() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")


def _mk_session() -> requests.Session:
    s = requests.Session()
    # trust_env=True to respect user's proxy env (HTTP(S)_PROXY), which may be required
    s.trust_env = True
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Referer": "https://vip.stock.finance.sina.com.cn/mkt/",
            "Connection": "close",
            "Accept": "*/*",
        }
    )
    return s


def _sleep_jitter(base: float) -> None:
    time.sleep(base + random.random() * base)


def fetch_node_page(
    session: requests.Session, node: str, page: int, num: int = 80, timeout: int = 25
) -> List[Dict]:
    params = zh_sina_a_stock_payload.copy()
    params.update(
        {
            "page": str(page),
            "num": str(num),
            "sort": "symbol",
            "asc": "1",
            "node": node,
            "symbol": "",
            "_s_r_a": "page",
        }
    )
    r = session.get(zh_sina_a_stock_url, params=params, timeout=timeout)
    # Sina sometimes returns 456 with HTML; treat as error and retry upstream
    if r.status_code != 200 or not r.text.strip().startswith("["):
        raise RuntimeError(f"bad response: status={r.status_code} len={len(r.text)}")
    data = demjson.decode(r.text)
    if not isinstance(data, list):
        raise RuntimeError("unexpected decoded payload type")
    return data


def fetch_node_all(
    session: requests.Session,
    node: str,
    sleep_sec: float = 0.15,
    max_pages: int = 500,
    max_retries_per_page: int = 8,
    retry_backoff_sec: float = 2.0,
) -> List[Dict]:
    out: List[Dict] = []
    page = 1
    while page <= max_pages:
        for attempt in range(1, max_retries_per_page + 1):
            try:
                items = fetch_node_page(session=session, node=node, page=page)
                break
            except Exception:
                if attempt == max_retries_per_page:
                    raise
                _sleep_jitter(retry_backoff_sec * attempt)
        if not items:
            break
        out.extend(items)
        page += 1
        _sleep_jitter(sleep_sec)
    return out


def _symbol_suffix_from_prefix(symbol: str) -> str:
    # Sina returns "sh600000", "sz000001", "bj920000"
    if symbol.startswith("sh"):
        return "SS"
    if symbol.startswith("sz"):
        return "SZ"
    if symbol.startswith("bj"):
        return "BJ"
    return ""


def build_universe_df(session: requests.Session, sleep_sec: float) -> pd.DataFrame:
    items = fetch_node_all(session=session, node="hs_a", sleep_sec=sleep_sec)
    df = pd.DataFrame(items)
    if df.empty:
        return df

    # Ensure expected fields
    keep = ["symbol", "code", "name", "trade", "mktcap", "nmc", "per", "pb", "turnoverratio"]
    for col in keep:
        if col not in df.columns:
            df[col] = None
    df = df[keep].copy()

    df["code"] = df["code"].astype(str).str.zfill(6)
    df["exchange"] = df["symbol"].astype(str).apply(_symbol_suffix_from_prefix)
    df["symbol_std"] = df["code"] + "." + df["exchange"]
    df["trade"] = pd.to_numeric(df["trade"], errors="coerce")
    df["mktcap_wan"] = pd.to_numeric(df["mktcap"], errors="coerce")
    df["nmc_wan"] = pd.to_numeric(df["nmc"], errors="coerce")
    df["total_mv_yi"] = df["mktcap_wan"] / 10000.0
    df["float_mv_yi"] = df["nmc_wan"] / 10000.0
    df["asof"] = _now_str()
    return df


def build_excluded_code_set(
    session: requests.Session, exclude_nodes: Iterable[str], sleep_sec: float
) -> Set[str]:
    excluded: Set[str] = set()
    for node in exclude_nodes:
        try:
            items = fetch_node_all(session=session, node=node, sleep_sec=sleep_sec)
            for it in items:
                code = str(it.get("code", "")).zfill(6)
                if code.isdigit():
                    excluded.add(code)
        except Exception:
            # If a node is temporarily blocked, skip it (caller can decide if this is acceptable)
            continue
    return excluded


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--threshold-yi", type=float, default=100.0, help="Threshold in 亿元 (default: 100).")
    p.add_argument(
        "--exclude-nodes",
        nargs="*",
        default=DEFAULT_EXCLUDE_INDUSTRY_NODES,
        help="Sina industry nodes to exclude (e.g. hangye_ZK70).",
    )
    p.add_argument("--sleep-sec", type=float, default=0.15, help="Base sleep between requests.")
    p.add_argument("--out-dir", type=str, default="results", help="Output directory.")
    args = p.parse_args()

    threshold_yi = float(args.threshold_yi)
    session = _mk_session()

    # Optional: get mapping label->板块 name for reporting
    industry_map: Dict[str, str] = {}
    try:
        ind_df = ak.stock_sector_spot(indicator="行业")
        industry_map = {str(r["label"]): str(r["板块"]) for _, r in ind_df.iterrows()}
    except Exception:
        industry_map = {}

    universe = build_universe_df(session=session, sleep_sec=float(args.sleep_sec))
    if universe.empty:
        print("[ERR] Failed to fetch hs_a universe.")
        return 2

    excluded_codes = build_excluded_code_set(
        session=session, exclude_nodes=args.exclude_nodes, sleep_sec=float(args.sleep_sec)
    )

    filtered = universe.copy()
    filtered = filtered[filtered["total_mv_yi"].notna()].copy()
    filtered = filtered[filtered["total_mv_yi"] >= threshold_yi].copy()
    if excluded_codes:
        filtered = filtered[~filtered["code"].isin(excluded_codes)].copy()

    filtered.sort_values(["total_mv_yi"], ascending=False, inplace=True)
    filtered.reset_index(drop=True, inplace=True)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"a_share_total_mv_ge_{int(threshold_yi)}yi_excl_sina_{stamp}.csv"
    txt_path = out_dir / f"a_share_codes_total_mv_ge_{int(threshold_yi)}yi_excl_sina_{stamp}.txt"
    meta_path = out_dir / f"a_share_total_mv_ge_{int(threshold_yi)}yi_excl_sina_{stamp}.meta.txt"

    filtered.to_csv(csv_path, index=False, encoding="utf-8-sig")
    filtered["symbol_std"].to_csv(txt_path, index=False, header=False, encoding="utf-8")

    excluded_named = [
        f"{n}({industry_map.get(n,'')})" if industry_map else n for n in args.exclude_nodes
    ]
    meta = [
        f"asof={_now_str()}",
        f"threshold_yi={threshold_yi}",
        f"universe_count={len(universe)}",
        f"excluded_nodes={excluded_named}",
        f"excluded_codes_count={len(excluded_codes)}",
        f"result_count={len(filtered)}",
        f"csv={csv_path}",
        f"txt={txt_path}",
    ]
    meta_path.write_text("\n".join(meta) + "\n", encoding="utf-8")

    print(f"[OK] Saved: {csv_path}")
    print(f"[OK] Saved: {txt_path}")
    print(f"[OK] Saved: {meta_path}")
    print(f"result_count={len(filtered)} | excluded_codes={len(excluded_codes)} | universe={len(universe)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

