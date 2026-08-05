from pathlib import Path
from src.ingest import ingest_portfolio
import polars as pl

if __name__ == "__main__":
    # Pops up File Explorer window to select Excel portfolio file
    df_stage1 = ingest_portfolio()
    
    with pl.Config(tbl_cols=-1, tbl_rows=-1):
        print("\nComplete Output Table (All Fields):")
        print(df_stage1)
        
    # 2. Option B: Convert to dictionary list to inspect row-by-row
    print("\nFirst Row Record Preview:")
    print(df_stage1.to_dicts()[0])