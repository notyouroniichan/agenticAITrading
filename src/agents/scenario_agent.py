import copy
import logging
from typing import Dict, List, Any
from src.models.schema import PortfolioSnapshot, PositionSnapshot

logger = logging.getLogger(__name__)

class ScenarioAgent:
    def __init__(self):
        pass

    def simulate_shock(self, snapshot: PortfolioSnapshot, shocks: Dict[str, float]) -> Dict[str, Any]:
        """
        Simulate a market shock on the portfolio.
        shocks: Dict of symbol/asset -> percentage move (e.g., {"BTC": -0.10, "ETH": 0.05})
        Returns: Dict with simulated equity and PnL change.
        """
        if not snapshot.positions:
            return {
                "original_equity": snapshot.total_equity_usd,
                "simulated_equity": snapshot.total_equity_usd,
                "pnl_impact": 0.0
            }

        simulated_equity = snapshot.total_equity_usd
        pnl_impact = 0.0
        
        # We need to simulate the change in unrealized PnL for each position
        # New PnL = (New Price - Entry Price) * Size (for Long)
        # New Price = Mark Price * (1 + shock)
        
        simulated_positions = []

        for pos in snapshot.positions:
            # Check if this asset has a shock defined
            # Simplified matching: check if shock key is in symbol string (e.g., "BTC" in "BTC/USDT")
            shock_pct = 0.0
            for asset, shock in shocks.items():
                if asset in pos.symbol:
                    shock_pct = shock
                    break
            
            if shock_pct == 0.0:
                continue
                
            original_mark = pos.mark_price
            new_mark = original_mark * (1 + shock_pct)
            
            # PnL Calculation
            # Long: (New - Entry) * Size
            # Short: (Entry - New) * Size
            
            if pos.side.lower() == 'long':
                new_pnl = (new_mark - pos.entry_price) * pos.size
            else:
                new_pnl = (pos.entry_price - new_mark) * pos.size
                
            pnl_change = new_pnl - pos.unrealized_pnl
            pnl_impact += pnl_change
            simulated_equity += pnl_change
            
            simulated_positions.append({
                "symbol": pos.symbol,
                "original_mark": original_mark,
                "new_mark": new_mark,
                "pnl_change": pnl_change
            })
            
        logger.info(f"Scenario Result: Impact=${pnl_impact:.2f}, New Equity=${simulated_equity:.2f}")
        
        return {
            "original_equity": snapshot.total_equity_usd,
            "simulated_equity": simulated_equity,
            "pnl_impact": pnl_impact,
            "details": simulated_positions
        }
