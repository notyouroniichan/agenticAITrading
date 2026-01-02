import logging
from typing import Dict, Any, Optional
from src.models.schema import PortfolioSnapshot
from src.core.logger import logger

class AttributionAgent:
    def __init__(self):
        pass

    def compute_attribution(self, current: PortfolioSnapshot, previous: Optional[PortfolioSnapshot]) -> Dict[str, Any]:
        """
        Decompose PnL Change.
        Simple MVP: Attribution = Current PnL - Previous PnL
        Split by Asset.
        """
        if not previous:
            return {"message": "No previous snapshot for attribution"}
            
        total_pnl_change = current.total_unrealized_pnl_usd - previous.total_unrealized_pnl_usd
        
        curr_pos_map = {p.symbol: p for p in current.positions}
        prev_pos_map = {p.symbol: p for p in previous.positions}
        
        breakdown = {}
        
        all_symbols = set(curr_pos_map.keys()) | set(prev_pos_map.keys())
        
        for sym in all_symbols:
            curr_p = curr_pos_map.get(sym)
            prev_p = prev_pos_map.get(sym)
            
            curr_val = curr_p.unrealized_pnl if curr_p else 0.0
            prev_val = prev_p.unrealized_pnl if prev_p else 0.0
            
            change = curr_val - prev_val
            if abs(change) > 0.01: # Filter noise
                breakdown[sym] = change
                
        logger.info(f"Attribution: Total Change=${total_pnl_change:.2f}")
        
        return {
            "total_pnl_change": total_pnl_change,
            "asset_attribution": breakdown
        }
