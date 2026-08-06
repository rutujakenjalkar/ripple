import os
import numpy as np
import pandas as pd
from src.factor_data import Fast_map_contract

def run_stage_4():
  print("--- RUNNING STAGE 4: PORTFOLIO BETA AGGREGATION ---")

  # 1. Read Processed Portfolio Data (Stage 1) and Beta Matrix (Stage 3)
  portfolio_path = "data/processed/portfolio_processed.csv"
  beta_path = "data/processed/beta_matrix.csv"

  if not os.path.exists(portfolio_path) or not os.path.exists(beta_path):
    raise FileNotFoundError(
        "Missing required inputs! Ensure Stage 1 and Stage 3 have executed"
        " successfully."
    )

  portfolio_df = pd.read_csv(portfolio_path)
  beta_df = pd.read_csv(beta_path, index_col=0)

  # 2. Map Excel contracts to Yahoo Finance Tickers
  portfolio_df["ticker"] = portfolio_df["contract"].apply(Fast_map_contract)

  # 3. Compute Portfolio Asset Weights (W) using actual Signed Notionals
  # Weight = Signed Notional / Total Portfolio Gross Absolute Value
  total_gross_notional = portfolio_df["signed_notional"].abs().sum()

  if total_gross_notional == 0:
    raise ValueError(
        "Total Portfolio Notional is 0. Check Stage 1 data inputs."
    )

  portfolio_df["weight"] = portfolio_df["signed_notional"] / total_gross_notional

  print("\n1. REAL PORTFOLIO POSITIONS & WEIGHTS:")
  print(
      portfolio_df[[
          "contract",
          "ticker",
          "direction",
          "signed_notional",
          "weight",
      ]].to_string(index=False)
  )

  # 4. Aggregate Weights by Unique Asset Ticker
  weight_by_ticker = portfolio_df.groupby("ticker")["weight"].sum()

  # Align Weight Vector with the exact row ordering of Stage 3 Beta Matrix
  weight_vector = weight_by_ticker.reindex(beta_df.index, fill_value=0.0)

  # 5. Matrix Product: beta_portfolio = W @ B_assets
  # (1 x N_assets) @ (N_assets x K_factors) -> (1 x K_factors)
  beta_portfolio = np.dot(weight_vector.values, beta_df.values)

  # Convert result to clean Series
  portfolio_beta_series = pd.Series(
      beta_portfolio, index=beta_df.columns, name="Portfolio_Beta"
  )

  # Zero out minor float precision residuals (< 1e-10)
  portfolio_beta_series = portfolio_beta_series.apply(
      lambda x: 0.0 if abs(x) < 1e-10 else x
  )

  # 6. Save Stage 4 Result
  os.makedirs("data/processed", exist_ok=True)
  output_df = portfolio_beta_series.to_frame()
  output_df.to_csv("data/processed/portfolio_beta_vector.csv")

  pd.set_option("display.float_format", lambda x: "%.6f" % x)

  print("\n=======================================================")
  print("--- 2. STAGE 4 OUTPUT: ACTUAL PORTFOLIO BETA VECTOR ---")
  print("=======================================================")
  print(output_df)
  print(
      "\nStage 4 complete! Saved vector to"
      " data/processed/portfolio_beta_vector.csv"
  )


if __name__ == "__main__":
  run_stage_4()