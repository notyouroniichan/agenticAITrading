import logging
import json
from openai import AsyncOpenAI
from typing import Dict, Any, Optional
from src.core.config import settings
from src.models.schema import PortfolioSnapshot, AnalyticsSnapshot

logger = logging.getLogger(__name__)

class LLMAnalystAgent:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("LLM Analyst initialized without API Key. Capabilities disabled.")

    async def generate_briefing(self, 
                                portfolio: PortfolioSnapshot, 
                                analytics: AnalyticsSnapshot,
                                risk_metrics: Dict[str, Any]) -> str:
        """
        Generate a daily briefing based on portfolio state and analytics.
        """
        if not self.client:
             return "LLM Analyst: No API Key provided or client not initialized."

        # Prepare context
        context = {
            "total_equity": portfolio.total_equity_usd,
            "unrealized_pnl": portfolio.total_unrealized_pnl_usd,
            "positions_count": len(portfolio.positions),
            "net_exposure": analytics.net_exposure_usd,
            "concentration_hhi": analytics.concentration_hhi,
            "drawdown": risk_metrics.get("rolling_drawdown_pct"),
            "var_95": risk_metrics.get("var_95_1d_pct"),
            "top_position": portfolio.positions[0].symbol if portfolio.positions else "None"
        }
        
        prompt = f"""
        You are a Senior Risk Analyst for a crypto hedge fund. 
        Analyze the following portfolio state and provide a concise executive summary.
        
        Data:
        {json.dumps(context, indent=2)}
        
        Requirements:
        1. Highlight key risks (Drawdown, Concentration).
        2. Comment on directional exposure.
        3. Use professional financial tone.
        4. Keep it under 200 words.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI portfolio analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error generating insight: {e}"
