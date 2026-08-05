import os
import pandas as pd
import statsmodels.api as sm
import time


def run_factor_regressions():
  print("Loading factor and asset returns...")

  # Load master files generated from Stage 2
  factor_returns = pd.read_csv(
      "data/processed/factor_returns.csv", index_col=0, parse_dates=True
  )
  asset_returns = pd.read_csv(
      "data/processed/asset_returns.csv", index_col=0, parse_dates=True
  )

  # Align dates cleanly
  common_index = asset_returns.index.intersection(factor_returns.index)
  asset_returns = asset_returns.loc[common_index]
  factor_returns = factor_returns.loc[common_index]

  # 1. Tag each Yahoo asset ticker with its specific futures asset category
  asset_categories = {
      "^NSEI": "equity",
      "^NSEBANK": "equity",
      "^GSPC": "equity",
      "CL=F": "energy",
      "BZ=F": "energy",
      "NG=F": "energy",
      "GC=F": "metal",
      "SI=F": "metal",
      "HG=F": "metal",
      "LE=F": "agri",
      "ZC=F": "agri",
      "ZW=F": "agri",
      "ZS=F": "agri",
      "EURUSD=X": "forex",
      "USDINR=X": "forex",
  }

  # 2. Define specific factor subsets for each asset category (Economic Logic)
  factor_mappings = {
      "equity": ["Growth", "Rates_Long", "Dollar", "Volatility"],
      "energy": ["Oil", "Gas", "Dollar", "Growth"],
      "metal": ["Gold", "Base_Metals", "Dollar", "Rates_Long"],
      "agri": ["Agri_Index", "Oil", "Dollar"],
      "forex": ["Dollar", "Rates_Long", "Growth"],
  }

  betas = {}
  r_squareds = {}

  print("\nRunning OLS Regressions with Custom Asset-Class Factor Mappings...")
  for asset in asset_returns.columns:
    y = asset_returns[asset]

    # Find category (defaults to equity if an asset isn't explicitly mapped)
    category = asset_categories.get(asset, "equity")
    relevant_factors = factor_mappings.get(
        category, factor_returns.columns.tolist()
    )

    # Subset factors for this specific asset class only and add constant
    X_subset = factor_returns[relevant_factors]
    X = sm.add_constant(X_subset)

    # Fit Ordinary Least Squares model
    model = sm.OLS(y, X).fit()

    # Extract coefficients and map back to full global factor columns (filling missing with 0.0)
    asset_betas = model.params[1:]
    full_beta_series = pd.Series(0.0, index=factor_returns.columns)
    full_beta_series[asset_betas.index] = asset_betas

    betas[asset] = full_beta_series
    r_squareds[asset] = model.rsquared

  # Convert results into structured DataFrames
  beta_df = pd.DataFrame(betas).T
  r2_df = pd.Series(r_squareds, name="R_Squared").to_frame()

  # Save final outputs to processed folder
  os.makedirs("data/processed", exist_ok=True)
  beta_df.to_csv("data/processed/beta_matrix.csv")
  r2_df.to_csv("data/processed/r_squared.csv")

  print("\n--- UNIFORM PORTFOLIO BETA MATRIX ---")
  print(beta_df)
  print(
      "\nSuccessfully saved custom-mapped beta matrix to"
      " data/processed/beta_matrix.csv"
  )


if __name__ == "__main__":
  start = time.perf_counter()
  run_factor_regressions()
  print(f"⏱️ Total Execution Time: {time.perf_counter() - start:.2f} seconds")