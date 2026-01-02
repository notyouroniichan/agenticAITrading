import logging
import numpy as np
import pandas as pd
import duckdb
from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.models.schema import PortfolioSnapshot, init_duckdb
from src.core.logger import logger

class RiskAgent:
    def __init__(self, market_db_path: str = "market_data.duckdb"):
        self.duck_conn = init_duckdb(market_db_path)

    def compute_metrics(self, snapshot: PortfolioSnapshot, equity_curve: List[float]) -> Dict[str, Any]:
        """
        Compute Risk Metrics: VaR and Drawdown.
        equity_curve: List of historical total_equity_usd values (chronological).
        """
        
        if not equity_curve:
            current_drawdown = 0.0
        else:
            peak = max(equity_curve)
            current = equity_curve[-1]
            if peak > 0:
                current_drawdown = (peak - current) / peak
            else:
                current_drawdown = 0.0
                
        
        total_var = 0.0
        z_score = 1.645
        
        for pos in snapshot.positions:
            vol = self._get_asset_volatility(pos.symbol)
            notional = pos.size * pos.mark_price
            pos_var = notional * vol * z_score
            total_var += pos_var
            
        var_pct = 0.0
        if snapshot.total_equity_usd > 0:
            var_pct = total_var / snapshot.total_equity_usd
            
        logger.info(f"Computed Risk: DD={current_drawdown:.2%}, VaR_95={var_pct:.2%}")
        
        return {
            "rolling_drawdown_pct": current_drawdown,
            "var_95_1d_pct": var_pct
        }

    def _get_asset_volatility(self, symbol: str) -> float:
        """
        Fetch annualized volatility for symbol from DuckDB.
        Returns 0.0 if insufficient data.
        """
        try:
            search_sym = symbol.replace("/", "").replace("-USD", "").replace("-", "")
            
            # Fetch last 24h of 'last' price
            q = f"""
                SELECT last, timestamp 
                FROM market_ticks 
                WHERE symbol ILIKE '%{search_sym}%'
                AND timestamp > now() - INTERVAL '1 day'
                ORDER BY timestamp ASC
            """
            
            # Use fetchdf to get pandas dataframe
            df = self.duck_conn.execute(q).fetchdf()
            
            if len(df) < 10:
                print(f"Warning: Insufficient vol data for {symbol} (found {len(df)} ticks)")
                return 0.0
                
            # Calculate simple realized volatility from tick returns (approximation)
            # Ideally resample to hourly
            df.set_index('timestamp', inplace=True)
            # Resample to hourly close to standardize
            hourly = df['last'].resample('h').last().dropna()
            
            if len(hourly) < 2:
                return 0.0
            
            returns = hourly.pct_change().dropna()
            vol = returns.std() * np.sqrt(24 * 365) # Annualized
            
            if np.isnan(vol):
                return 0.0
                
            logger.info(f"Computed Volatility for {symbol}: {vol:.2%}")
            return vol
            
        except Exception as e:
            logger.error(f"Error calculating vol for {symbol}: {e}")
            return 0.0 
