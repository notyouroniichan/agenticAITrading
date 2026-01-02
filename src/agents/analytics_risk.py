import logging
import numpy as np
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
        
        # 1. Rolling Drawdown
        # DD = (Peak - Current) / Peak
        if not equity_curve:
            current_drawdown = 0.0
        else:
            peak = max(equity_curve)
            current = equity_curve[-1]
            if peak > 0:
                current_drawdown = (peak - current) / peak
            else:
                current_drawdown = 0.0
                
        # 2. Parametric VaR (95% 1-day)
        # Simplified: Sum of individual position VaRs (no correlation matrix for MVP)
        # VaR_pos = Notional * Volatility * Z_score (1.645 for 95%)
        # Volatility: fetch trailing 30d vol from DuckDB
        
        total_var = 0.0
        z_score = 1.645
        
        for pos in snapshot.positions:
            vol = self._get_asset_volatility(pos.symbol)
            notional = pos.size * pos.mark_price
            pos_var = notional * vol * z_score
            total_var += pos_var
            
        # VaR as % of Equity
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
        MVP: Return hardcoded/mock vol if no data.
        """
        # TODO: Implement actual SQL query on market_ticks
        # SELECT stddev(returns) ...
        # For MVP, returning generic crypto vol ~3% daily
        return 0.03 
