# config/mappings.py
import polars as pl

COLUMN_ALIASES = {
    "contract": ["contract", "ticker", "symbol", "contract_id", "contract/ticker"],
    "exchange": ["exchange", "venue"],
    "direction": ["direction", "side", "pos_type"],
    "entry_date": ["entry_date", "trade_date", "date"],
    "contracts": ["contracts", "qty", "quantity", "position_size", "position"],
    "entry_price": ["entry_price", "avg_price", "average_price"],
    "current_price": ["current_price", "ltp", "market_price", "price"],
    "contract_multiplier": ["contract_multiplier", "lot_size", "point_value", "multiplier"],
    "previous_settlement_price": [
        "previous_settlement_price",
        "settlement_price",
        "prev_settlement",
        "prior_settlement",
    ],
    "expiry_date": ["expiry_date", "expiration_date", "expiry", "expiry_date_/_trading_symbol"],
}

REQUIRED_COLUMNS = {
    "contract",
    "exchange",
    "direction",
    "entry_date",
    "contracts",
    "entry_price",
    "current_price",
    "contract_multiplier",
    "previous_settlement_price",
    "expiry_date",
}

# Target Polars Data Types for Schema Enforcing
SCHEMA_TYPES = {
    "contract": pl.Utf8,
    "exchange": pl.Utf8,
    "direction": pl.Utf8,
    "entry_date": pl.Utf8,
    "contracts": pl.Int64,
    "entry_price": pl.Float64,
    "current_price": pl.Float64,
    "contract_multiplier": pl.Float64,
    "previous_settlement_price": pl.Float64,
    "expiry_date": pl.Utf8,
}