import os
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
  print(f"⏱️ Total Execution Time: {time.perf_counter() - start:.2f} seconds")