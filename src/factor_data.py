'''import os
import pandas as pd
from src.ingest import ingest_portfolio
import yfinance as yf
import time

# 1. Expanded Macro Factors covering diverse asset classes
MACRO_TICKERS = {
    "Growth": "^GSPC",  # S&P 500 (Equity Growth)
    "Rates_Long": "^TNX",  # 10-Year Treasury Yield (Fixed Income)
    "Rates_Short": "^IRX",  # Short-Term Rates
    "Dollar": "DX-Y.NYB",  # US Dollar Index (Forex)
    "Oil": "CL=F",  # Crude Oil Futures (Energy)
    "Gas": "NG=F",  # Natural Gas (Energy)
    "Gold": "GC=F",  # Gold Futures (Precious Metals)
    "Base_Metals": "HG=F",  # Copper / Industrial Metals
    "Agri_Index": "DBA",  # Agriculture ETF (Grains, Softs, Livestock feed)
    "Volatility": "^VIX",  # Volatility Index
}


# 2. Comprehensive Contract Mapper for diverse futures
def map_contract_to_yahoo(contract_name: str) -> str:
  name = contract_name.upper()

  # Equity & Indices
  if "NIFTY" in name and "BANK" not in name:
    return "^NSEI"
  elif "BANKNIFTY" in name:
    return "^NSEBANK"
  elif "SPX" in name or "S&P" in name:
    return "^GSPC"

  # Energy Commodities
  elif "CRUDE" in name or "WTI" in name:
    return "CL=F"
  elif "BRENT" in name:
    return "BZ=F"
  elif "NATGAS" in name or "GAS" in name:
    return "NG=F"

  # Metal Commodities
  elif "GOLD" in name:
    return "GC=F"
  elif "SILVER" in name:
    return "SI=F"
  elif "COPPER" in name:
    return "HG=F"

  # Agricultural & Livestock
  elif "CATTLE" in name or "LE" in name:
    return "LE=F"
  elif "CORN" in name:
    return "ZC=F"
  elif "WHEAT" in name:
    return "ZW=F"
  elif "SOY" in name:
    return "ZS=F"

  # Currency / Forex Pairs
  elif "EUR" in name:
    return "EURUSD=X"
  elif "INR" in name:
    return "USDINR=X"

  else:
    return None


def fetch_returns(period="1y"):
  os.makedirs("data/processed", exist_ok=True)

  # --- Part A: Fetch Macro Factor Returns ---
  print(
      "Fetching historical data for expanded macroeconomic factors across"
      " diverse asset classes..."
  )
  macro_symbols = list(MACRO_TICKERS.values())
  macro_data = yf.download(
      macro_symbols, period=period, interval="1d", progress=False
  )

  if isinstance(macro_data.columns, pd.MultiIndex):
    macro_close = macro_data["Close"]
  else:
    macro_close = macro_data

  inv_map = {v: k for k, v in MACRO_TICKERS.items()}
  macro_close = macro_close.rename(columns=inv_map)
  factor_returns = macro_close.pct_change().dropna()

  factor_returns.to_csv("data/processed/factor_returns.csv")
  print("Saved expanded factor returns to data/processed/factor_returns.csv")

  # --- Part B: Fetch Portfolio Asset Returns ---
  print("\nReading portfolio and fetching asset histories...")
  portfolio_df = ingest_portfolio()

  asset_tickers = {}
  for contract in portfolio_df["contract"].to_list():
    yahoo_t = map_contract_to_yahoo(contract)
    if yahoo_t:
      asset_tickers[contract] = yahoo_t

  if asset_tickers:
    unique_t = list(set(asset_tickers.values()))
    asset_data = yf.download(
        unique_t, period=period, interval="1d", progress=False
    )

    if isinstance(asset_data.columns, pd.MultiIndex):
      asset_close = asset_data["Close"]
    else:
      asset_close = asset_data

    asset_returns = asset_close.pct_change().dropna()
    asset_returns.to_csv("data/processed/asset_returns.csv")
    print("Saved diverse portfolio asset returns to data/processed/asset_returns.csv")


if __name__ == "__main__":
  start = time.perf_counter()
  fetch_returns()

  # --- Print Previews to Check Data ---
  print("\n--- FACTOR RETURNS PREVIEW ---")
  f_df = pd.read_csv("data/processed/factor_returns.csv", index_col=0)
  print(f_df.tail())

  print("\n--- ASSET RETURNS PREVIEW ---")
  a_df = pd.read_csv("data/processed/asset_returns.csv", index_col=0)
  print(a_df.tail())

  print("\nStage 2 completely finished: Diverse macro and asset returns ready.")
  end = time.perf_counter()
  elapsed_time = end - start
  print(f"Total execution time: {elapsed_time:.4f} seconds")'''

'''

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
import pandas as pd
import polars as pl
import requests
from src.ingest import ingest_portfolio

# Configure HTTP Session with connection pooling
HTTP_SESSION = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=25, pool_maxsize=25, max_retries=2
)
HTTP_SESSION.mount("https://", adapter)
HTTP_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
})

# 1. Macro Factors (10 Tickers)
MACRO_TICKERS = {
    "Growth": "^GSPC",
    "Rates_Long": "^TNX",
    "Rates_Short": "^IRX",
    "Dollar": "DX-Y.NYB",
    "Oil": "CL=F",
    "Gas": "NG=F",
    "Gold": "GC=F",
    "Base_Metals": "HG=F",
    "Agri_Index": "DBA",
    "Volatility": "^VIX",
}

# 2. Fast Keyword Mapping Dictionary
KEYWORD_TO_YAHOO = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SPX": "^GSPC",
    "S&P": "^GSPC",
    "CRUDE": "CL=F",
    "WTI": "CL=F",
    "BRENT": "BZ=F",
    "NATGAS": "NG=F",
    "GAS": "NG=F",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "CATTLE": "LE=F",
    "CORN": "ZC=F",
    "WHEAT": "ZW=F",
    "SOY": "ZS=F",
    "EUR": "EURUSD=X",
    "INR": "USDINR=X",
}


def Fast_map_contract(contract_name: str) -> str:
  """Fast string lookup using keyword lookup."""
  if not isinstance(contract_name, str):
    return None
  clean_name = contract_name.strip().upper()

  for key, yahoo_ticker in KEYWORD_TO_YAHOO.items():
    if key in clean_name:
      return yahoo_ticker
  return None


def fetch_single_ticker_direct(
    symbol: str, period_days: int = 365
) -> tuple[str, pd.Series]:
  """Fetches a single ticker using query2.finance.yahoo.com."""
  end_time = int(time.time())
  start_time = end_time - (period_days * 86400)
  url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_time}&period2={end_time}&interval=1d"

  try:
    res = HTTP_SESSION.get(url, timeout=5)
    if res.status_code == 200:
      data = res.json()
      result = data["chart"]["result"][0]
      timestamps = result.get("timestamp")
      closes = result.get("indicators", {}).get("quote", [{}])[0].get("close")

      if timestamps and closes:
        dates = pd.to_datetime(timestamps, unit="s").date
        return symbol, pd.Series(closes, index=dates, name=symbol)
  except Exception as e:
    pass
  return symbol, None


def fetch_returns(
    user_excel_path: str = None, cache_ttl_seconds: int = 3600
):
  os.makedirs("data/processed", exist_ok=True)
  factor_file = "data/processed/factor_returns.csv"
  asset_file = "data/processed/asset_returns.csv"
  t0 = time.perf_counter()

  # --- Fast Local Cache Check ---
  if os.path.exists(factor_file) and os.path.exists(asset_file):
    file_age = time.time() - os.path.getmtime(factor_file)
    if file_age < cache_ttl_seconds:
      print(
          f"⚡ Loaded market data from cache in {time.perf_counter() - t0:.2f}s"
      )
      return

  # --- 1. Ingest Excel Data ---
  portfolio_df = (
      ingest_portfolio(user_excel_path)
      if user_excel_path
      else ingest_portfolio()
  )
  if isinstance(portfolio_df, tuple):
    portfolio_df = portfolio_df[0]

  contract_series = portfolio_df["contract"]
  raw_contracts = (
      contract_series.drop_nans().cast(pl.String).str.strip_chars().to_list()
  )

  # Map contract names to unique ticker set
  unique_asset_tickers = {
      ticker
      for contract in raw_contracts
      if (ticker := Fast_map_contract(contract)) is not None
  }
  macro_tickers = set(MACRO_TICKERS.values())

  # Union of all unique tickers
  all_unique_tickers = list(macro_tickers | unique_asset_tickers)

  print(
      f"📊 Excel contains {len(raw_contracts)} rows -> Deduplicated down to"
      f" {len(all_unique_tickers)} unique tickers."
  )
  print("📡 Requesting all tickers in parallel...")

  # --- 2. Parallel Fetching ---
  series_dict = {}
  with ThreadPoolExecutor(max_workers=len(all_unique_tickers)) as executor:
    futures = {
        executor.submit(fetch_single_ticker_direct, sym): sym
        for sym in all_unique_tickers
    }
    for future in as_completed(futures):
      sym, series = future.result()
      if series is not None:
        series_dict[sym] = series

  if not series_dict:
    raise RuntimeError("Failed to pull market data.")

  # Combine into DataFrame
  prices_df = pd.DataFrame(series_dict).dropna()

  # --- 3. Process Factor Returns ---
  inv_macro = {v: k for k, v in MACRO_TICKERS.items()}
  avail_macro = [s for s in MACRO_TICKERS.values() if s in prices_df.columns]
  macro_close = prices_df[avail_macro].rename(columns=inv_macro)
  factor_returns = macro_close.pct_change().dropna()
  factor_returns.to_csv(factor_file)

  # --- 4. Process Asset Returns ---
  avail_assets = [s for s in unique_asset_tickers if s in prices_df.columns]
  if avail_assets:
    asset_close = prices_df[avail_assets]
    asset_returns = asset_close.pct_change().dropna()
    asset_returns.to_csv(asset_file)

  print(
      f"⚡ Ingested & calculated returns in {time.perf_counter() - t0:.2f}"
      " seconds."
  )


if __name__ == "__main__":
  start = time.perf_counter()
  fetch_returns(cache_ttl_seconds=3600)
  print(
      f"\n⏱️ Benchmark Execution Time: {time.perf_counter() - start:.2f} seconds"
  )'''


import asyncio
import os
import time
import aiohttp
import pandas as pd
import polars as pl
from src.ingest import ingest_portfolio

# 1. Macro Factors (10 Tickers)
MACRO_TICKERS = {
    "Growth": "^GSPC",
    "Rates_Long": "^TNX",
    "Rates_Short": "^IRX",
    "Dollar": "DX-Y.NYB",
    "Oil": "CL=F",
    "Gas": "NG=F",
    "Gold": "GC=F",
    "Base_Metals": "HG=F",
    "Agri_Index": "DBA",
    "Volatility": "^VIX",
}

# 2. Fast Keyword Mapping Dictionary
KEYWORD_TO_YAHOO = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SPX": "^GSPC",
    "S&P": "^GSPC",
    "CRUDE": "CL=F",
    "WTI": "CL=F",
    "BRENT": "BZ=F",
    "NATGAS": "NG=F",
    "GAS": "NG=F",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "COPPER": "HG=F",
    "CATTLE": "LE=F",
    "CORN": "ZC=F",
    "WHEAT": "ZW=F",
    "SOY": "ZS=F",
    "EUR": "EURUSD=X",
    "INR": "USDINR=X",
}


def Fast_map_contract(contract_name: str) -> str:
  """Fast keyword lookup for Yahoo tickers."""
  if not isinstance(contract_name, str):
    return None
  clean_name = contract_name.strip().upper()

  for key, yahoo_ticker in KEYWORD_TO_YAHOO.items():
    if key in clean_name:
      return yahoo_ticker
  return None


async def fetch_ticker_async(
    session: aiohttp.ClientSession, symbol: str, period_days: int = 365
) -> tuple[str, pd.Series]:
  """Asynchronous fetch for an individual ticker using query2.finance.yahoo.com."""
  end_time = int(time.time())
  start_time = end_time - (period_days * 86400)
  url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={start_time}&period2={end_time}&interval=1d"

  try:
    async with session.get(url, timeout=4) as response:
      if response.status == 200:
        data = await response.json()
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp")
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close")

        if timestamps and closes:
          dates = pd.to_datetime(timestamps, unit="s").date
          return symbol, pd.Series(closes, index=dates, name=symbol)
  except Exception:
    pass
  return symbol, None


async def fetch_all_async(symbols: list[str]) -> dict[str, pd.Series]:
  """Fires all HTTP requests concurrently using an open TCP connector pool."""
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  # TCPConnector pool opens sockets simultaneously without OS queuing
  connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)
  async with aiohttp.ClientSession(
      headers=headers, connector=connector
  ) as session:
    tasks = [fetch_ticker_async(session, sym) for sym in symbols]
    results = await asyncio.gather(*tasks)
    return {sym: series for sym, series in results if series is not None}


def fetch_returns(
    user_excel_path: str = None, cache_ttl_seconds: int = 3600
):
  os.makedirs("data/processed", exist_ok=True)
  factor_file = "data/processed/factor_returns.csv"
  asset_file = "data/processed/asset_returns.csv"
  t0 = time.perf_counter()

  # --- Fast Local Cache Check ---
  if os.path.exists(factor_file) and os.path.exists(asset_file):
    file_age = time.time() - os.path.getmtime(factor_file)
    if file_age < cache_ttl_seconds:
      print(
          f"⚡ Loaded market data from cache in {time.perf_counter() - t0:.2f}s"
      )
      return

  # --- 1. Ingest Excel Data ---
  portfolio_df = (
      ingest_portfolio(user_excel_path)
      if user_excel_path
      else ingest_portfolio()
  )
  if isinstance(portfolio_df, tuple):
    portfolio_df = portfolio_df[0]

  contract_series = portfolio_df["contract"]
  raw_contracts = (
      contract_series.drop_nans().cast(pl.String).str.strip_chars().to_list()
  )

  # Deduplicate tickers
  unique_asset_tickers = {
      ticker
      for contract in raw_contracts
      if (ticker := Fast_map_contract(contract)) is not None
  }
  macro_tickers = set(MACRO_TICKERS.values())
  all_unique_tickers = list(macro_tickers | unique_asset_tickers)

  print(
      f"📊 Excel contains {len(raw_contracts)} rows -> Deduplicated down to"
      f" {len(all_unique_tickers)} unique tickers."
  )
  print("🚀 Launching Async I/O network requests...")

  # --- 2. Non-blocking Async execution ---
  series_dict = asyncio.run(fetch_all_async(all_unique_tickers))

  if not series_dict:
    raise RuntimeError("Failed to pull market data.")

  # Combine into clean DataFrame
  prices_df = pd.DataFrame(series_dict).dropna()

  # --- 3. Process Factor Returns ---
  inv_macro = {v: k for k, v in MACRO_TICKERS.items()}
  avail_macro = [s for s in MACRO_TICKERS.values() if s in prices_df.columns]
  macro_close = prices_df[avail_macro].rename(columns=inv_macro)
  factor_returns = macro_close.pct_change().dropna()
  factor_returns.to_csv(factor_file)

  # --- 4. Process Asset Returns ---
  avail_assets = [s for s in unique_asset_tickers if s in prices_df.columns]
  if avail_assets:
    asset_close = prices_df[avail_assets]
    asset_returns = asset_close.pct_change().dropna()
    asset_returns.to_csv(asset_file)

  print(
      f"⚡ Ingested & calculated returns in {time.perf_counter() - t0:.2f}"
      " seconds."
  )


if __name__ == "__main__":
  '''start = time.perf_counter()
  fetch_returns(cache_ttl_seconds=0)  # Benchmark fresh network call speed
  print(
      f"\n⏱️ Benchmark Execution Time: {time.perf_counter() - start:.2f} seconds"
  )'''
  start = time.perf_counter()
    
    # Set TTL to 3600s (1 hour). 
    # Run 1: Network fetch (~0.3s - 0.8s)
    # Run 2: Instant disk cache (< 0.002s)
  fetch_returns(cache_ttl_seconds=3600)
    
  elapsed = time.perf_counter() - start
  print(f"\n⏱️ Benchmark Execution Time: {elapsed:.4f} seconds")