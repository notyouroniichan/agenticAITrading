import asyncio
import logging
from datetime import datetime
from src.agents.market_data import MarketDataAgent
from src.agents.portfolio_state import PortfolioStateAgent
from src.agents.analytics_exposure import ExposureAgent
from src.agents.analytics_risk import RiskAgent
from src.agents.analytics_attribution import AttributionAgent
from src.agents.llm_analyst import LLMAnalystAgent
from src.models.schema import AnalyticsSnapshot
from src.core.config import settings

logger = logging.getLogger(__name__)

class SystemOrchestrator:
    def __init__(self, use_memory_db: bool = False):
        self.market_agent = MarketDataAgent(db_path=":memory:" if use_memory_db else "market_data.duckdb")
        self.portfolio_agent = PortfolioStateAgent(db_url="sqlite+aiosqlite:///:memory:" if use_memory_db else settings.DATABASE_URL)
        self.exposure_agent = ExposureAgent()
        self.risk_agent = RiskAgent(market_db_path=":memory:" if use_memory_db else "market_data.duckdb")
        self.attribution_agent = AttributionAgent()
        self.llm_agent = LLMAnalystAgent()
        self.running = False

    async def start(self):
        self.running = True
        logger.info("Initializing Orchestrator...")
        
        asyncio.create_task(self.market_agent.start())
        await self.portfolio_agent.init_db()
        
        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(60) # Run every minute
            except Exception as e:
                logger.error(f"Orchestrator Cycle Error: {e}")
                await asyncio.sleep(5)

    async def run_cycle(self):
        logger.info("--- Starting Analytics Cycle ---")
        
        snapshot = await self.portfolio_agent.fetch_snapshot()
        
        exp_metrics = self.exposure_agent.compute_metrics(snapshot)
        
        equity_curve = [100000.0, snapshot.total_equity_usd] 
        risk_metrics = self.risk_agent.compute_metrics(snapshot, equity_curve)
        
        analytics_snap = AnalyticsSnapshot(
            snapshot_id=snapshot.id,
            gross_exposure_usd=exp_metrics['gross_exposure_usd'],
            net_exposure_usd=exp_metrics['net_exposure_usd'],
            concentration_hhi=exp_metrics['concentration_hhi'],
            rolling_drawdown_pct=risk_metrics['rolling_drawdown_pct'],
            var_95_1d_pct=risk_metrics['var_95_1d_pct']
        )
        
        
        logger.info(f"Cycle Complete. Equity=${snapshot.total_equity_usd:.2f}, VaR={risk_metrics['var_95_1d_pct']:.2%}")
        

    async def stop(self):
        self.running = False
        await self.market_agent.stop()
