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
        
        gross_exposure = 0.0
        net_exposure = 0.0
        
        asset_weights = {}
        total_notional = 0.0
        
        for pos in snapshot.positions:
            notional = pos.size * pos.mark_price
            gross_exposure += notional
            
            if pos.side.lower() == 'long':
                net_exposure += notional
            else:
                net_exposure -= notional
                
            sym = pos.symbol
            asset_weights[sym] = asset_weights.get(sym, 0.0) + notional
            total_notional += notional
            
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
