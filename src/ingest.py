import re
import difflib
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import polars as pl
from config.mappings import COLUMN_ALIASES, REQUIRED_COLUMNS, SCHEMA_TYPES

def select_file_via_explorer() -> Path:
    """Opens OS native File Explorer to select an Excel file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    
    file_path = filedialog.askopenfilename(
        title="Select Portfolio Excel File",
        filetypes=[("Excel Files", "*.xlsx *.xls")]
    )
    
    if not file_path:
        raise FileNotFoundError("No file selected. Operation cancelled by user.")
        
    return Path(file_path)

def normalize_str(s: str) -> str:
    """Removes all special characters, spaces, and lowers case for flexible matching."""
    return re.sub(r'[^a-z0-9]', '', str(s).lower())

def map_excel_headers(df_columns: list[str]) -> dict[str, str]:
    """Matches raw Excel column names to standard keys using exact normalized lookups."""
    renames = {}
    
    # 1. Build a direct lookup table mapping every normalized alias to its canonical target key
    alias_to_target = {}
    for target_key, aliases in COLUMN_ALIASES.items():
        all_aliases = set(aliases) | {target_key}
        for alias in all_aliases:
            alias_to_target[normalize_str(alias)] = target_key

    # 2. First Pass: Exact normalized matching
    for raw_col in df_columns:
        norm_raw = normalize_str(raw_col)
        if norm_raw in alias_to_target:
            target = alias_to_target[norm_raw]
            if target not in renames.values():
                renames[raw_col] = target

    # 3. Second Pass: Fuzzy matching for remaining unmapped columns
    unmapped_raw = [col for col in df_columns if col not in renames]
    for raw_col in unmapped_raw:
        norm_raw = normalize_str(raw_col)
        matches = difflib.get_close_matches(norm_raw, list(alias_to_target.keys()), n=1, cutoff=0.7)
        if matches:
            target = alias_to_target[matches[0]]
            if target not in renames.values():
                renames[raw_col] = target

    return renames

def clean_and_cast(df: pl.DataFrame) -> pl.DataFrame:
    """Extracts numeric values from unit strings (e.g. '100 g' -> 100.0) and casts data types."""
    
    # Extract numbers if contract_multiplier contains text like '100 g' or '30 kg'
    if df["contract_multiplier"].dtype == pl.Utf8:
        df = df.with_columns(
            pl.col("contract_multiplier")
            .str.extract(r"(\d+\.?\d*)", 1)
            .cast(pl.Float64)
            .alias("contract_multiplier")
        )

    # Enforce schema datatypes & normalize direction
    expressions = []
    for col_name, dtype in SCHEMA_TYPES.items():
        if col_name == "direction":
            expressions.append(pl.col(col_name).str.strip_chars().str.to_uppercase().alias(col_name))
        else:
            expressions.append(pl.col(col_name).cast(dtype).alias(col_name))

    return df.with_columns(expressions)

def compute_derived_fields(df: pl.DataFrame) -> pl.DataFrame:
    """Calculates direction sign, total signed notional, and unrealized trade P&L."""
    return df.with_columns([
        # Direction Sign (+1.0 for LONG, -1.0 for SHORT)
        pl.when(pl.col("direction") == "LONG")
          .then(1.0)
          .otherwise(-1.0)
          .alias("direction_sign"),
        
        # Total Signed Notional Value
        (
            pl.when(pl.col("direction") == "LONG").then(1.0).otherwise(-1.0)
            * pl.col("contracts")
            * pl.col("contract_multiplier")
            * pl.col("current_price")
        ).alias("signed_notional"),
        
        # Trade P&L = (Current Price - Entry Price) * Direction Sign * Contracts * Multiplier
        (
            (pl.col("current_price") - pl.col("entry_price"))
            * pl.when(pl.col("direction") == "LONG").then(1.0).otherwise(-1.0)
            * pl.col("contracts")
            * pl.col("contract_multiplier")
        ).alias("unrealized_pnl")
    ])

def ingest_portfolio(input_path: Path = None, output_dir: Path = Path("data/processed")) -> pl.DataFrame:
    """Stage 1 Execution Engine."""
    if input_path is None:
        input_path = select_file_via_explorer()
        
    print(f"[Stage 1] Loading selected Excel file: {input_path}")
    
    # 1. Read Raw Excel File
    df_raw = pl.read_excel(source=str(input_path))
    
    # 2. Map Column Names
    header_mapping = map_excel_headers(df_raw.columns)
    df_mapped = df_raw.rename(header_mapping)
    
    # 3. Check for Missing Required Columns
    missing_cols = REQUIRED_COLUMNS - set(df_mapped.columns)
    if missing_cols:
        raise ValueError(
            f"Missing required columns in input file: {missing_cols}\n"
            f"Mapped columns found: {list(df_mapped.columns)}"
        )

    # 4. Filter Schema & Clean Types
    df_filtered = df_mapped.select(list(REQUIRED_COLUMNS))
    df_cleaned = clean_and_cast(df_filtered)
    
    # 5. Calculate Notionals & PnL
    df_processed = compute_derived_fields(df_cleaned)
    
    # 6. Save Processed Dataset
    output_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = output_dir / "portfolio_processed.parquet"
    csv_path = output_dir / "portfolio_processed.csv"
    
    df_processed.write_parquet(parquet_path)
    df_processed.write_csv(csv_path)
    
    print(f"[Stage 1] Success! Processed data saved to {parquet_path}")
    return df_processed

if __name__ == "__main__":
    df = ingest_portfolio()
    print("\nStage 1 Data Preview:")
    print(df.select(["contract", "direction", "contracts", "signed_notional", "unrealized_pnl"]))