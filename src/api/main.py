import asyncio
import logging
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from src.core.orchestrator import SystemOrchestrator
from src.models.schema import PortfolioSnapshot, AnalyticsSnapshot
from src.agents.scenario_agent import ScenarioAgent
from src.agents.llm_analyst import LLMAnalystAgent

logger = logging.getLogger(__name__)

orchestrator = SystemOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting API & Orchestrator...")
    asyncio.create_task(orchestrator.start())
    yield
    logger.info("Shutting down API...")
    await orchestrator.stop()

app = FastAPI(title="Agentic Portfolio Analytics API", lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "running", "environment": "development"}

from src.models.schema import PortfolioDTO

@app.get("/snapshot/latest")
async def get_latest_snapshot():
    """Retrieve the absolute latest portfolio state from memory or DB."""
    snap = await orchestrator.portfolio_agent.fetch_snapshot()
    
    portfolio_dto = PortfolioDTO.model_validate(snap)
    
    exp = orchestrator.exposure_agent.compute_metrics(snap)
    risk = orchestrator.risk_agent.compute_metrics(snap, [100000, snap.total_equity_usd])
    
    return {
        "portfolio": portfolio_dto,
        "analytics": {
            "exposure": exp,
            "risk": risk
        }
    }

@app.post("/scenario/simulate")
async def run_scenario(shocks: dict[str, float]):
    """Run a market shock simulation."""
    agent = ScenarioAgent()
    current_snap = await orchestrator.portfolio_agent.fetch_snapshot()
    result = agent.simulate_shock(current_snap, shocks)
    return result

@app.post("/agent/ask")
async def ask_agent():
    """Trigger LLM Analyst manually."""
    current_snap = await orchestrator.portfolio_agent.fetch_snapshot()
    return {"message": "Agent interface ready. (Integration pending detailed connect)"}
