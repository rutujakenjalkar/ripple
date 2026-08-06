import os
import pandas as pd
import numpy as np
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional, List
import dotenv

dotenv.load_dotenv()

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

ALL_FACTORS = list(MACRO_TICKERS.keys())

class FactorItem(BaseModel):
    factor_name: str = Field(..., description="The exact macro factor name.")
    has_news: bool = Field(..., description="True if there is active breaking news today, False otherwise.")
    old_value: Optional[float] = Field(None, description="Previous numerical value if a transition is mentioned (e.g., 4.5).")
    new_value: Optional[float] = Field(None, description="New numerical value if a transition is mentioned (e.g., 4.2).")
    single_pct: Optional[float] = Field(None, description="Exact percentage change as a single number if stated (e.g., 1.5 for +1.5%).")
    absolute_level: Optional[float] = Field(None, description="Absolute market level reading if given without change (e.g., 49.5 for PMI).")
    direction: str = Field("FLAT", description="Must be 'UP', 'DOWN', or 'FLAT' if no numbers are present.")
    headline_summary: str = Field(..., description="Brief factual summary or quote from the news headline.")

class MacroNewsExtraction(BaseModel):
    overall_summary: str = Field(..., description="Executive summary of market news.")
    factor_impacts: List[FactorItem] = Field(..., description="Impacts for all macro factors.")

def validate_and_sanitize_shock(pct_val: float) -> float:
    """
    Deterministic Python guardrail to ensure LLM hallucinations never corrupt the hedge matrix.
    Threshold set to 15% to allow normal market moves while blocking wild AI errors.
    """
    if pct_val is None or pd.isna(pct_val):
        return 0.0
    
    MAX_REALISTIC_MOVE = 0.15 
    
    if abs(pct_val) > MAX_REALISTIC_MOVE:
        print(f"⚠️ [Guardrail Warning] Extreme hallucination detected ({pct_val*100:+.2f}%). Clamped to 0.0% to protect hedge accuracy.")
        return 0.0
        
    return pct_val

def get_macro_multipliers() -> dict:
    """
    Parses live macro news via LLM, applies Python guardrails, and returns 
    a clean dictionary mapping each macro factor name to its final multiplier (1.0 + pct_val).
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    prompt = f"""
    Analyze current global financial market news for these macro factors: {ALL_FACTORS}
    
    Strict extraction guidelines:
    - If no news exists, set `has_news` to False and `direction` to 'FLAT'.
    - If news shows a transition (e.g. 'moved from 4.5 to 4.2'), fill `old_value` and `new_value`.
    - If news states a single percentage change (e.g. 'surged 1.5%'), fill `single_pct` with 1.5.
    - If news gives an absolute index/reading (e.g. 'PMI at 49.5'), fill `absolute_level`.
    - If no numbers exist, set `direction` to 'UP', 'DOWN', or 'FLAT'.
    """
    
    print("\nFetching and parsing live macro news securely...")
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system", 
                "content": "You are a precise quantitative risk parser. Extract raw figures cleanly without doing arbitrary calculations."
            },
            {"role": "user", "content": prompt}
        ],
        response_format=MacroNewsExtraction,
    )
    
    parsed = completion.choices[0].message.parsed
    impact_dict = {item.factor_name: item for item in parsed.factor_impacts}
    
    gamma_multipliers = {}
    
    print("\n=======================================================")
    print("--- MACRO FACTORS & MULTIPLIERS EXTRACTION AUDIT ---")
    print("=======================================================")
    
    for factor in ALL_FACTORS:
        item = impact_dict.get(factor)
        
        if not item or not item.has_news:
            pct_val = 0.0
        elif item.old_value is not None and item.new_value is not None:
            pct_val = (item.new_value - item.old_value) / item.old_value
        elif item.single_pct is not None:
            pct_val = item.single_pct / 100.0
        elif item.absolute_level is not None:
            if factor == "Growth" and item.absolute_level < 50.0:
                pct_val = -0.015
            else:
                pct_val = 0.005
        else:
            standard_shock = 0.015
            if item.direction == "UP":
                pct_val = standard_shock
            elif item.direction == "DOWN":
                pct_val = -standard_shock
            else:
                pct_val = 0.0
        
        # Apply strict guardrail
        pct_val = validate_and_sanitize_shock(pct_val)
        
        # Compute final multiplier
        multiplier = 1.0 + pct_val
        gamma_multipliers[factor] = multiplier
        
        print(f"Factor: {factor:<15} | Multiplier: {multiplier:.4f} (Shift: {pct_val*100:+.2f}%)")
            
    return gamma_multipliers

if __name__ == "__main__":
    multipliers = get_macro_multipliers()
    print("\nFinal Extracted Multipliers Dictionary:")
    print(multipliers)