import logging
import asyncio
from typing import Dict, Any, Tuple
from src.models.schema import PortfolioSnapshot
from src.core.logger import logger

class ExposureAgent:
    def __init__(self):
        pass

    def compute_metrics(self, snapshot: PortfolioSnapshot) -> Dict[str, Any]:
        """
        Calculate exposure and concentration metrics for a given portfolio snapshot.
        Returns a dictionary suitable for AnalyticsSnapshot model.
        """
        if not snapshot.positions:
            return {
                "gross_exposure_usd": 0.0,
                "net_exposure_usd": 0.0,
                "concentration_hhi": 0.0
            }

        total_equity = snapshot.total_equity_usd
        
        # 1. Gross & Net Exposure
        gross_exposure = 0.0
        net_exposure = 0.0
        
        # For HHI, we need weights of individual assets (grouped by symbol/base asset)
        # We'll use absolute notional value for weight calculation
        asset_weights = {}
        total_notional = 0.0
        
        for pos in snapshot.positions:
            notional = pos.size * pos.mark_price
            gross_exposure += notional
            
            if pos.side.lower() == 'long':
                net_exposure += notional
            else:
                net_exposure -= notional
                
            # Group by symbol for HHI (simplified, better to group by base asset)
            # Assuming symbol is unique asset for now or closely related
            sym = pos.symbol
            asset_weights[sym] = asset_weights.get(sym, 0.0) + notional
            total_notional += notional
            
        # 2. HHI Calculation
        # HHI = Sum of squared weights (s_i^2) where s_i is market share (0 to 1 or 0 to 100)
        # We will use 0 to 1 scale.
        hhi = 0.0
        if total_notional > 0:
            for val in asset_weights.values():
                weight = val / total_notional
                hhi += weight ** 2
        
        logger.info(f"Computed Exposure: Gross=${gross_exposure:.2f}, Net=${net_exposure:.2f}, HHI={hhi:.4f}")
        
        return {
            "gross_exposure_usd": gross_exposure,
            "net_exposure_usd": net_exposure,
            "concentration_hhi": hhi
        }
