from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Float, DateTime, Integer, JSON, create_engine, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pydantic import BaseModel, ConfigDict
import duckdb

# --- SQLAlchemy Models (Portfolio State) ---

class Base(DeclarativeBase):
    pass

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    total_equity_usd: Mapped[float] = mapped_column(Float)
    total_margin_used_usd: Mapped[float] = mapped_column(Float)
    total_unrealized_pnl_usd: Mapped[float] = mapped_column(Float)
    
    # Store aggregated breakdown as JSON for flexible querying
    # e.g., {"BTC": {"net_exposure": 1.2, "value": 50000}, ...}
    asset_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON)
    
    positions: Mapped[List["PositionSnapshot"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")

class PositionSnapshot(Base):
    __tablename__ = "position_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("portfolio_snapshots.id"))
    
    venue: Mapped[str] = mapped_column(String(50)) # e.g., 'binance', 'hyperliquid'
    symbol: Mapped[str] = mapped_column(String(50)) # e.g., 'BTC/USDT'
    side: Mapped[str] = mapped_column(String(10)) # 'long', 'short'
    size: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    mark_price: Mapped[float] = mapped_column(Float)
    unrealized_pnl: Mapped[float] = mapped_column(Float)
    leverage: Mapped[float] = mapped_column(Float, nullable=True)
    
    snapshot: Mapped["PortfolioSnapshot"] = relationship(back_populates="positions")

class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("portfolio_snapshots.id"), unique=True)
    
    # Exposure Metrics
    gross_exposure_usd: Mapped[float] = mapped_column(Float)
    net_exposure_usd: Mapped[float] = mapped_column(Float)
    concentration_hhi: Mapped[float] = mapped_column(Float) # Herfindahl-Hirschman Index
    
    # Risk Metrics
    rolling_drawdown_pct: Mapped[float] = mapped_column(Float)
    var_95_1d_pct: Mapped[float] = mapped_column(Float)
    
    # Attribution (JSON for flexibility)
    attribution_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    
    snapshot: Mapped["PortfolioSnapshot"] = relationship(back_populates="analytics")

# Update PortfolioSnapshot to include relation
PortfolioSnapshot.analytics = relationship("AnalyticsSnapshot", uselist=False, back_populates="snapshot")


# --- Pydantic Data Transfer Objects ---

class MarketTicker(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    venue: str
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last: float
    volume_24h: Optional[float] = None

class NormalizedPosition(BaseModel):
    venue: str
    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    liquidation_price: Optional[float] = None
    leverage: Optional[float] = None
    collateral: Optional[float] = None

# --- DuckDB Initialization (Market Data) ---

def init_duckdb(db_path: str = "market_data.duckdb"):
    con = duckdb.connect(db_path)
    
    # Market Ticks Table
    con.execute("""
        CREATE TABLE IF NOT EXISTS market_ticks (
            venue VARCHAR,
            symbol VARCHAR,
            timestamp TIMESTAMP,
            bid DOUBLE,
            ask DOUBLE,
            last DOUBLE,
            volume_24h DOUBLE
        )
    """)
    
    # Funding Rates Table
    con.execute("""
        CREATE TABLE IF NOT EXISTS funding_rates (
            venue VARCHAR,
            symbol VARCHAR,
            timestamp TIMESTAMP,
            rate DOUBLE,
            predicted_rate DOUBLE
        )
    """)
    
    return con
    return con

# --- API Response DTOs ---

class PositionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    venue: str
    side: str
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    leverage: Optional[float] = None

class PortfolioDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    timestamp: datetime
    total_equity_usd: float
    total_unrealized_pnl_usd: float
    asset_breakdown: Optional[Dict[str, Any]] = None
    positions: List[PositionDTO] = []
