import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Agentic AI Portfolio",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Config
API_URL = "http://localhost:8000"

def fetch_data():
    try:
        response = requests.get(f"{API_URL}/snapshot/latest")
        if response.status_code == 200:
            return response.json()
    except Exception:
        return None
    return None

def simulate_shock(shocks):
    try:
        response = requests.post(f"{API_URL}/scenario/simulate", json=shocks)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Simulation failed: {e}")
    return None

st.title("Agentic Portfolio Intelligence")

# Main Data Fetch
data = fetch_data()

if not data:
    st.error("Backend API is disconnected. Please run `uvicorn src.api.main:app`.")
    st.stop()

portfolio = data.get("portfolio", {})
analytics = data.get("analytics", {})
positions = portfolio.get("positions", [])

# --- Sidebar ---
st.sidebar.header("Control Panel")
st.sidebar.success("System Status: Online")
st.sidebar.info(f"Last Update: {portfolio.get('timestamp')}")

# --- Top Key Metrics ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Equity", f"${portfolio.get('total_equity_usd', 0):,.2f}")
with col2:
    pnl = portfolio.get('total_unrealized_pnl_usd', 0)
    st.metric("Unrealized PnL", f"${pnl:,.2f}", delta_color="normal" if pnl >= 0 else "inverse")
with col3:
    var = analytics.get('risk', {}).get('var_95_1d_pct', 0)
    st.metric("VaR (95%)", f"{var:.2%}")
with col4:
    hhi = analytics.get('exposure', {}).get('concentration_hhi', 0)
    st.metric("Concentration (HHI)", f"{hhi:.2f}")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["Portfolio Overview", "Scenario Lab", "Risk Intelligence"])

with tab1:
    # Asset Allocation
    st.subheader("Asset Allocation")
    if positions:
        df_pos = pd.DataFrame(positions)
        df_pos['value'] = df_pos['size'] * df_pos['mark_price']
        
        c1, c2 = st.columns(2)
        with c1:
            fig_alloc = px.pie(df_pos, values='value', names='symbol', title="Portfolio Composition")
            st.plotly_chart(fig_alloc, use_container_width=True)
        with c2:
            st.dataframe(df_pos)
    else:
        st.info("No open positions.")

with tab2:
    st.subheader("Market Simulator")
    st.write("Simulate market shocks to see portfolio impact.")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        btc_shock = st.slider("BTC Move (%)", -50, 50, 0)
        eth_shock = st.slider("ETH Move (%)", -50, 50, 0)
    
    if st.button("Run Simulation"):
        shocks = {}
        if btc_shock != 0: shocks["BTC"] = btc_shock / 100.0
        if eth_shock != 0: shocks["ETH"] = eth_shock / 100.0
        
        sim_res = simulate_shock(shocks)
        
        if sim_res:
            res_col1, res_col2 = st.columns(2)
            res_col1.metric("Simulated Equity", f"${sim_res.get('simulated_equity', 0):,.2f}",
                            delta=f"{sim_res.get('pnl_impact', 0):,.2f}")
            
            # Show details table
            st.write("Impact Details:")
            st.dataframe(pd.DataFrame(sim_res.get('details', [])))

with tab3:
    st.subheader("Risk Analytics")
    risk_data = analytics.get('risk', {})
    
    st.markdown(f"""
    **Rolling Drawdown**: {risk_data.get('rolling_drawdown_pct', 0):.2%}
    
    **Value at Risk (1D 95%)**: {risk_data.get('var_95_1d_pct', 0):.2%}
    """)
    
    # Placeholder for chart
    st.info("Historical risk charts require database history populate.")
