import os
import pandas as pd
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List
import dotenv
from dotenv import load_dotenv



load_dotenv()
# Your 10 Macro Factors
MACRO_TICKERS = {
    "Growth": "^GSPC",       # S&P 500
    "Rates_Long": "^TNX",    # 10-Yr Yield
    "Rates_Short": "^IRX",   # Short-Term Rates
    "Dollar": "DX-Y.NYB",    # USD Index
    "Oil": "CL=F",           # Crude Oil
    "Gas": "NG=F",           # Natural Gas
    "Gold": "GC=F",          # Gold
    "Base_Metals": "HG=F",   # Copper
    "Agri_Index": "DBA",     # Agriculture
    "Volatility": "^VIX",    # VIX
}

ALL_FACTORS = list(MACRO_TICKERS.keys())

# -------------------------------------------------------------------
# 1. OpenAI Strict-Compliant Pydantic Schema (No Defaults, Explicit List)
# -------------------------------------------------------------------
class FactorItem(BaseModel):
    factor_name: str = Field(
        ..., 
        description="The exact macro factor name from the provided list (e.g., Gold, Oil, Dollar)."
    )
    pct_change: float = Field(
        ..., 
        description="Decimal percentage shift (e.g., +0.15 for +15%, -0.05 for -5%, 0.0 for no news)."
    )
    key_facts: List[str] = Field(
        ..., 
        description="List of specific factual headlines or market events that justify this shift."
    )

class MacroNewsExtractionWithFacts(BaseModel):
    overall_summary: str = Field(
        ..., 
        description="Executive summary of current global market news."
    )
    factor_impacts: List[FactorItem] = Field(
        ..., 
        description="List of impacts for all requested macro factors."
    )

# -------------------------------------------------------------------
# 2. News Fetching & Testing Function
# -------------------------------------------------------------------
def test_news_and_percentage_changes():
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    prompt = f"""
    1. Retrieve and analyze current global financial market news and macroeconomic developments today.
    2. Evaluate market impacts for every single factor in this list:
       {ALL_FACTORS}
    3. For every factor, state specific market facts or news events in `key_facts`.
    4. Provide the estimated percentage shift in `pct_change` (e.g., +0.10 for +10%, -0.05 for -5%). 
       If no news exists for a factor, set `pct_change` to 0.0 and `key_facts` to ["No significant news today"].
    """
    
    print("\nSending request to OpenAI API...")
    
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system", 
                "content": "You are a quantitative risk manager. Extract macro factor shocks and base all percentage shifts strictly on verifiable facts."
            },
            {"role": "user", "content": prompt}
        ],
        response_format=MacroNewsExtractionWithFacts,
    )
    
    parsed = completion.choices[0].message.parsed
    
    print("\n=======================================================")
    print("--- EXECUTIVE NEWS SUMMARY ---")
    print("=======================================================")
    print(parsed.overall_summary)
    
    print("\n=======================================================")
    print("--- FACTUAL DECISION & PERCENTAGE CHANGE AUDIT LOG ---")
    print("=======================================================")
    
    # Map returned list items into a lookup dictionary
    impact_dict = {item.factor_name: item for item in parsed.factor_impacts}
    
    results = []
    
    for factor in ALL_FACTORS:
        item = impact_dict.get(factor)
        
        pct_val = item.pct_change if item else 0.0
        facts = item.key_facts if item else ["No news returned"]
        
        pct_display = f"{pct_val * 100:+.2f}%"
        multiplier = 1.0 + pct_val
        
        print(f"\nFactor: [{factor}]")
        print(f"  • Percentage Change: {pct_display}")
        print(f"  • Beta Multiplier:   {multiplier:.4f}")
        print("  • Supporting Evidence:")
        for fact in facts:
            print(f"      - {fact}")
            
        results.append({
            "Factor": factor,
            "Pct_Change": pct_display,
            "Multiplier": multiplier
        })
        
    print("\n=======================================================")
    print("--- FINAL MULTIPLIER SUMMARY TABLE ---")
    print("=======================================================")
    df_summary = pd.DataFrame(results).set_index("Factor")
    print(df_summary)

if __name__ == "__main__":
    test_news_and_percentage_changes()