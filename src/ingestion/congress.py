"""
Congressional STOCK Act disclosures via Quiver Quantitative.

The 'demo' API key returns ~1000 real records at no cost, no registration.
Set QUIVER_QUANT_KEY in .env to a real key for higher rate limits.

Fetch chain:
  1. Quiver Quant API  — live data (demo key or real key)
  2. Stale disk cache  — last good payload if live fails
  3. Demo seed data    — pipeline never crashes
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[2] / ".env")

QUIVER_URL = "https://api.quiverquant.com/beta/live/congresstrading"
CACHE_PATH = Path(__file__).parents[2] / "data" / "cache" / "congress_transactions.json"
CACHE_TTL_HOURS = 6

# ── demo seed ─────────────────────────────────────────────────────────────────
_SEED_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "JPM", "GOOGL", "META", "UNH", "V"]
_SEED_POLITICIANS = [
    ("Nancy Pelosi", "D", "house"),
    ("Dan Crenshaw", "R", "house"),
    ("Tommy Tuberville", "R", "senate"),
    ("Ro Khanna", "D", "house"),
    ("Michael McCaul", "R", "house"),
    ("Gary Peters", "D", "senate"),
    ("Richard McCormick", "R", "house"),
    ("Shelley Capito", "R", "senate"),
]
_SEED_TX_TYPES = ["Purchase", "Sale", "Sale (Full)"]
_SEED_RANGES = [
    "$1,001 - $15,000",
    "$15,001 - $50,000",
    "$50,001 - $100,000",
    "$100,001 - $250,000",
    "$250,001 - $500,000",
]


def _generate_demo_data(count: int = 24) -> list:
    import random
    rng = random.Random(42)
    today = datetime.now()
    data = []
    for i in range(count):
        name, party, chamber = rng.choice(_SEED_POLITICIANS)
        days_ago = rng.randint(1, 60)
        tx_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        report_date = (today - timedelta(days=max(0, days_ago - rng.randint(0, 5)))).strftime("%Y-%m-%d")
        data.append({
            "Representative": name,
            "BioGuideID": f"B{i:04d}",
            "ReportDate": report_date,
            "TransactionDate": tx_date,
            "Ticker": rng.choice(_SEED_TICKERS),
            "Transaction": rng.choice(_SEED_TX_TYPES),
            "Range": rng.choice(_SEED_RANGES),
            "House": "Senate" if chamber == "senate" else "Representatives",
            "Party": party,
            "TickerType": "ST",
            "Description": None,
            "ExcessReturn": round(rng.uniform(-8.0, 12.0), 2),
            "PriceChange": round(rng.uniform(-5.0, 8.0), 2),
            "SPYChange": round(rng.uniform(-3.0, 4.0), 2),
        })
    return data


# ── cache helpers ─────────────────────────────────────────────────────────────

def _cache_fresh() -> bool:
    if not CACHE_PATH.exists():
        return False
    return (datetime.now() - datetime.fromtimestamp(CACHE_PATH.stat().st_mtime)) < timedelta(hours=CACHE_TTL_HOURS)


def _load_cache() -> list:
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_cache(data: list) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(data, f)
        tmp.replace(CACHE_PATH)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


# ── Quiver Quant fetch ────────────────────────────────────────────────────────

def _fetch_quiver() -> list:
    api_key = os.getenv("QUIVER_QUANT_KEY", "demo")
    resp = requests.get(
        QUIVER_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "detail" in data:
        raise RuntimeError(f"Quiver API error: {data['detail']}")
    return data


def fetch_transactions(force_refresh: bool = False, verbose: bool = True) -> list:
    if not force_refresh and _cache_fresh():
        if verbose:
            print("      Using fresh cache")
        return _load_cache()

    try:
        data = _fetch_quiver()
        _save_cache(data)
        if verbose:
            print(f"      Fetched {len(data)} records from Quiver Quant")
        return data
    except Exception as e:
        if verbose:
            print(f"      Quiver Quant failed: {e}")

    if CACHE_PATH.exists():
        if verbose:
            print("      Falling back to stale cache")
        return _load_cache()

    if verbose:
        print("      WARNING: Using DEMO seed data — trades are simulated")
    data = _generate_demo_data()
    _save_cache(data)
    return data


# ── normalise to internal schema ──────────────────────────────────────────────

def normalize(raw: dict) -> dict:
    tx_raw = (raw.get("Transaction") or "").lower().strip()
    if "purchase" in tx_raw or "buy" in tx_raw:
        trade_type = "purchase"
    elif "sale (full)" in tx_raw or "full" in tx_raw:
        trade_type = "sale_full"
    elif "sale" in tx_raw or "sell" in tx_raw:
        trade_type = "sale"
    else:
        trade_type = tx_raw or "unknown"

    house = raw.get("House", "Representatives")
    source = "senate" if house == "Senate" else "house"

    return {
        "source": source,
        "representative": raw.get("Representative", "Unknown"),
        "ticker": (raw.get("Ticker") or "").upper().strip(),
        "asset_description": raw.get("Description") or "",
        "trade_type": trade_type,
        "amount_range": raw.get("Range", ""),
        "transaction_date": raw.get("TransactionDate", ""),
        "disclosure_date": raw.get("ReportDate", ""),
        "district": raw.get("Party", ""),
        "excess_return": raw.get("ExcessReturn"),
        "price_change": raw.get("PriceChange"),
        "spy_change": raw.get("SPYChange"),
    }


def get_recent_trades(days: int = 90, tickers_only: bool = True) -> list:
    raw = fetch_transactions()
    cutoff = datetime.now() - timedelta(days=days)
    results = []
    for row in raw:
        date_str = row.get("TransactionDate", "")
        try:
            trade_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if trade_date < cutoff:
            continue
        normalized = normalize(row)
        if tickers_only and not normalized["ticker"]:
            continue
        results.append(normalized)
    results.sort(key=lambda x: x["transaction_date"], reverse=True)
    return results


if __name__ == "__main__":
    trades = get_recent_trades(days=90)
    print(f"Found {len(trades)} trades in last 90 days\n")
    for t in trades[:10]:
        print(
            f"[{t['transaction_date']}] {t['representative']:30s} "
            f"{t['trade_type'].upper():10s} {t['ticker']:6s} {t['amount_range']:25s} ({t['source']})"
        )
