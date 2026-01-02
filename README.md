# Agentic AI Portfolio Analytics & Risk System

A professional-grade, locally hosted, agent-based system for real-time crypto portfolio monitoring, risk analytics, and decision support.

Built with **FastAPI**, **Streamlit**, **DuckDB**, **SQLAlchemy**, and **OpenAI**.

## 🚀 Features

### 1. Multi-Exchange Connectivity
-   **Binance Futures**: Real-time position fetching via `ccxt`.
-   **Hyperliquid**: On-chain position tracking via JSON-RPC.
-   **OKX**: Swap/Perpetual position tracking.
-   **Delta Exchange**: Options and Futures tracking.
-   **Unified Data Model**: All positions normalized to a standard format for aggregation.

### 2. Real-Time Analytics
-   **Exposure Analysis**: Gross Exposure, Net Exposure, and Concentration (HHI).
-   **Risk Metrics**:
    -   **Rolling Drawdown**: Track peak-to-trough decline.
    -   **Parametric VaR**: 95% 1-Day Value-at-Risk estimation.
-   **Attribution**: Decompose PnL changes by asset (e.g., "BTC contributed +$500").

### 3. Agentic Intelligence
-   **Market Scenario Simulator**: Simulate shocks (e.g., "BTC -10%") and see instant impact on Equity and Margin.
-   **LLM Analyst**: Integrated OpenAI agent that acts as a Senior Risk Officer, generating daily briefings and risk alerts based on your actual portfolio data.

### 4. Interactive Dashboard
-   **Streamlit UI**: Responsive dark-mode dashboard.
-   **Live Updates**: Auto-refreshing data.
-   **Visualizations**: Equity curves, risk gauges, and exposure heatmaps using Plotly.

### 5. Automated Reporting
-   **PDF Generation**: One-click generation of professional Risk Briefing PDFs.

---

## 🛠️ Installation

### Prerequisites
-   Python 3.10+
-   Git

### Setup
1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd agenticAITrading
    ```

2.  **Create virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -e .
    ```

4.  **Configuration**:
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and populate your keys:
    ```ini
    # Database (Defaults to local SQLite)
    DATABASE_URL=sqlite+aiosqlite:///./portfolio.db
    
    # LLM (Required for Analyst Agent)
    OPENAI_API_KEY=sk-...
    
    # Exchanges (Leave empty if not using)
    BINANCE_API_KEY=...
    BINANCE_API_SECRET=...
    HYPERLIQUID_WALLET_ADDRESS=0x...
    OKX_API_KEY=...
    OKX_SECRET=...
    OKX_PASSWORD=...
    DELTA_API_KEY=...
    DELTA_SECRET=...
    ```

---

## ▶️ Usage

The system consists of two parts: the **Backend API** (Brain) and the **Frontend UI** (Dashboard).

### 1. Start the Backend
Runs the Orchestrator, Agents, and API server.
```bash
uvicorn src.api.main:app --reload
```
*Port: 8000*

### 2. Start the Dashboard
Runs the visual interface.
```bash
streamlit run src/ui/dashboard.py
```
*Port: 8501 (Opens in browser)*

---

## 🏗️ Architecture

The system follows an **Agentic Architecture** where specialized agents handle distinct responsibilities:

-   **MarketDataAgent**: Ingests ticks and funding rates (DuckDB).
-   **PortfolioStateAgent**: Aggregates positions from all connected exchanges (SQLAlchemy).
-   **RiskAgent**: Computes VaR and Drawdown.
-   **ExposureAgent**: Computes HHI and Net Exposure.
-   **LLMAnalystAgent**: Synthesizes metrics into human-readable insights.
-   **SystemOrchestrator**: Manages the lifecycle and data flow between agents.

Data flows from **Exchanges** -> **Portfolio Agent** -> **Analytics Agents** -> **Dashboard/LLM**.

---

## 🔌 Extending: Adding New Exchanges

The system is designed to be easily extensible using `ccxt`.

1.  **Update Config**:
    Add your new keys to `src/core/config.py` (pydantic settings) and `.env`.

2.  **Update Portfolio Agent**:
    Edit `src/agents/portfolio_state.py`.
    
    Add a new fetch method:
    ```python
    async def _fetch_newexchange_positions(self) -> List[NormalizedPosition]:
        # Initialize exchange
        exchange = ccxt.newexchange({'apiKey': ..., 'secret': ...})
        
        # Fetch and Normalize
        raw = await exchange.fetch_positions()
        positions = []
        for p in raw:
            # Map fields to NormalizedPosition(venue="newexchange", ...)
            positions.append(...)
            
        await exchange.close()
        return positions
    ```

3.  **Register Fetcher**:
    Update the `fetch_snapshot` method in `PortfolioStateAgent` to call your new function and add it to the `all_positions` list:
    ```python
    new_positions = await self._fetch_newexchange_positions()
    all_positions = ... + new_positions
    ```

That's it! The Orchestrator, Analytics, and Dashboard will automatically process and display the new data.

---

## 🔮 Future Improvements

### 1. Order Management System (OMS)
-   **Goal**: Enable secure trade execution directly from the interface.
-   **Features**:
    -   Unified order entry ticket (Limit, Market, Stop).
    -   Smart routing to the appropriate exchange based on symbol.
    -   "Basket Trading" to execute multiple orders simultaneously.

### 2. Active Risk Management System
-   **Goal**: Transition from "Monitoring" to "Active Protection".
-   **Features**:
    -   **Kill Switch**: Automatically flatten positions if Drawdown exceeds X%.
    -   **Auto-Hedging**: Automatically open a short hedge if Beta exposure gets too high.
    -   **Pre-Trade Checks**: Block orders that would violate Max Leverage or Concentration limits.

