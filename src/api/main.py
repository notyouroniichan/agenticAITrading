import asyncio
import logging
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from src.core.orchestrator import SystemOrchestrator
from src.models.schema import PortfolioSnapshot, AnalyticsSnapshot
from src.agents.scenario_agent import ScenarioAgent
from src.agents.llm_analyst import LLMAnalystAgent

logger = logging.getLogger(__name__)

# Global Orchestrator Instance
orchestrator = SystemOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting API & Orchestrator...")
    asyncio.create_task(orchestrator.start())
    yield
    # Shutdown
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
    # For MVP, we'll fetch direct from agent (stateful) or DB
    # Using orchestrator's agent state for speed
    snap = await orchestrator.portfolio_agent.fetch_snapshot()
    
    # Convert ORM -> Pydantic to avoid recursion error
    portfolio_dto = PortfolioDTO.model_validate(snap)
    
    # Also reuse latest analytics
    # In real app, query DB. Here, we trigger a fresh quick compute
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
    # Get current state
    current_snap = await orchestrator.portfolio_agent.fetch_snapshot()
    result = agent.simulate_shock(current_snap, shocks)
    return result

@app.post("/agent/ask")
async def ask_agent():
    """Trigger LLM Analyst manually."""
    # MVP: Just return a mock or simple string if no key, else call agent
    # This requires constructing parameters from current state
    current_snap = await orchestrator.portfolio_agent.fetch_snapshot()
    # Mocking analytics objs for the call
    # In production, pass real objects
    return {"message": "Agent interface ready. (Integration pending detailed connect)"}
