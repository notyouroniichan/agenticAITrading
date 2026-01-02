import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import ccxt.async_support as ccxt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from src.core.config import settings
from src.models.schema import Base, PortfolioSnapshot, PositionSnapshot, NormalizedPosition

logger = logging.getLogger(__name__)

class PortfolioStateAgent:
    def __init__(self, db_url: str = settings.DATABASE_URL):
        self.engine = create_async_engine(db_url)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        self.binance = None
        self.hyperliquid_address = settings.HYPERLIQUID_WALLET_ADDRESS
        
    async def init_db(self):
        """Initialize the database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def fetch_snapshot(self) -> PortfolioSnapshot:
        """Fetch current state from all exchanges and aggregate."""
        timestamp = datetime.now()
        
        # 1. Fetch from exchanges (Parallel)
        binance_positions = await self._fetch_binance_positions()
        hyper_positions = await self._fetch_hyperliquid_positions() 
        okx_positions = await self._fetch_okx_positions()
        delta_positions = await self._fetch_delta_positions()
        
        all_positions = binance_positions + hyper_positions + okx_positions + delta_positions
        
        total_equity = 0.0 
        total_margin = 0.0
        total_upnl = 0.0
        
        position_snapshots = []
        asset_breakdown = {}
        
        for pos in all_positions:
            total_margin += (pos.size * pos.entry_price) / pos.leverage if pos.leverage else 0
            total_upnl += pos.unrealized_pnl
            
            base_asset = pos.symbol.split('/')[0] if '/' in pos.symbol else pos.symbol
            if base_asset not in asset_breakdown:
                asset_breakdown[base_asset] = {"net_exposure": 0.0}
            
            asset_breakdown[base_asset]["net_exposure"] += pos.size
            
            position_snapshots.append(PositionSnapshot(
                venue=pos.venue,
                symbol=pos.symbol,
                side=pos.side,
                size=pos.size,
                entry_price=pos.entry_price,
                mark_price=pos.mark_price,
                unrealized_pnl=pos.unrealized_pnl,
                leverage=pos.leverage
            ))

        total_equity = total_margin + total_upnl 

        snapshot = PortfolioSnapshot(
            timestamp=timestamp,
            total_equity_usd=total_equity,
            total_margin_used_usd=total_margin,
            total_unrealized_pnl_usd=total_upnl,
            asset_breakdown=asset_breakdown,
            positions=position_snapshots
        )
        
        await self._persist_snapshot(snapshot)
        return snapshot

    async def _persist_snapshot(self, snapshot: PortfolioSnapshot):
        async with self.async_session() as session:
            session.add(snapshot)
            await session.commit()
            logger.info(f"Persisted snapshot ID: {snapshot.id} with {len(snapshot.positions)} positions")


    async def _fetch_binance_positions(self) -> List[NormalizedPosition]:
        """Fetch positions from Binance Futures."""
        positions = []
        if not (settings.BINANCE_API_KEY and settings.BINANCE_API_SECRET):
            return []
            
        try:
            exchange = ccxt.binance({
                'apiKey': settings.BINANCE_API_KEY,
                'secret': settings.BINANCE_API_SECRET,
                'options': {'defaultType': 'future'}
            })
            
            
            raw_positions = await exchange.fetch_positions()
            active_positions = [p for p in raw_positions if float(p['contracts']) > 0]
            
            for p in active_positions:
                size = float(p['contracts'])
                entry_price = float(p['entryPrice'])
                mark_price = float(p.get('markPrice', p['entryPrice'])) # Fallback
                side = p['side'] # 'long' or 'short'
                unrealized_pnl = float(p['unrealizedPnl'])
                leverage = float(p['leverage'])
                
                positions.append(NormalizedPosition(
                    venue="binance",
                    symbol=p['symbol'],
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=unrealized_pnl,
                    leverage=leverage
                ))
                
            await exchange.close()
        except Exception as e:
            logger.error(f"Binance fetch error: {e}")
            
        return positions


    async def _fetch_okx_positions(self) -> List[NormalizedPosition]:
        """Fetch positions from OKX."""
        positions = []
        if not (settings.OKX_API_KEY and settings.OKX_SECRET and settings.OKX_PASSWORD):
            return []
            
        try:
            exchange = ccxt.okx({
                'apiKey': settings.OKX_API_KEY,
                'secret': settings.OKX_SECRET,
                'password': settings.OKX_PASSWORD,
                'options': {'defaultType': 'swap'} # Perpetuals
            })
            
            raw_positions = await exchange.fetch_positions()
            for p in raw_positions:
                size = float(p['contracts']) if p.get('contracts') else float(p['amount'])
                if size == 0: continue
                
                item_side = p['side'] 
                side = item_side if item_side else ('long' if size > 0 else 'short')
                
                entry_price = float(p.get('entryPrice') or 0)
                mark_price = float(p.get('markPrice') or entry_price)
                unrealized_pnl = float(p.get('unrealizedPnl') or 0)
                leverage = float(p.get('leverage') or 1)
                
                positions.append(NormalizedPosition(
                    venue="okx",
                    symbol=p['symbol'],
                    side=side,
                    size=abs(size), # normalize to positive
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=unrealized_pnl,
                    leverage=leverage
                ))
            await exchange.close()
        except Exception as e:
            logger.error(f"OKX fetch error: {e}")
            
        return positions

    async def _fetch_delta_positions(self) -> List[NormalizedPosition]:
        """Fetch positions from Delta Exchange."""
        positions = []
        if not (settings.DELTA_API_KEY and settings.DELTA_SECRET):
            return []
            
        try:
            exchange = ccxt.delta({
                'apiKey': settings.DELTA_API_KEY,
                'secret': settings.DELTA_SECRET
            })
            
            raw_positions = await exchange.fetch_positions()
            for p in raw_positions:
                size = float(p['contracts']) if p.get('contracts') else float(p['amount'])
                if size == 0: continue
                
                item_side = p['side']
                side = item_side if item_side else ('long' if size > 0 else 'short')
                
                entry_price = float(p.get('entryPrice') or 0)
                mark_price = float(p.get('markPrice') or entry_price)
                unrealized_pnl = float(p.get('unrealizedPnl') or 0)
                leverage = float(p.get('leverage') or 1)
                
                positions.append(NormalizedPosition(
                    venue="delta",
                    symbol=p['symbol'],
                    side=side,
                    size=abs(size),
                    entry_price=entry_price,
                    mark_price=mark_price,
                    unrealized_pnl=unrealized_pnl,
                    leverage=leverage
                ))
            await exchange.close()
        except Exception as e:
            logger.error(f"Delta fetch error: {e}")
            


    async def _fetch_hyperliquid_positions(self) -> List[NormalizedPosition]:
        """Fetch positions from Hyperliquid API."""
        positions = []
        if not self.hyperliquid_address:
            return []
            
        url = "https://api.hyperliquid.xyz/info"
        payload = {
            "type": "clearinghouseState",
            "user": self.hyperliquid_address
        }
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        asset_positions = data.get("assetPositions", [])
                        
                        for item in asset_positions:
                            pos = item.get("position", {})
                            coin = pos.get("coin", "UNKNOWN")
                            sze = float(pos.get("szi", 0))
                            
                            if sze == 0:
                                continue
                                
                            side = "long" if sze > 0 else "short"
                            size = abs(sze)
                            entry_price = float(pos.get("entryPx", 0))
                            
                            unrealized_pnl = float(pos.get("unrealizedPnl", 0))
                            mark_price = entry_price # Placeholder if not derived
                            
                            if size > 0:
                                if side == "long":
                                    mark_price = (unrealized_pnl / size) + entry_price
                                else:
                                    mark_price = entry_price - (unrealized_pnl / size)
                            
                            positions.append(NormalizedPosition(
                                venue="hyperliquid",
                                symbol=f"{coin}-USD",
                                side=side,
                                size=size,
                                entry_price=entry_price,
                                mark_price=mark_price,
                                unrealized_pnl=unrealized_pnl,
                                leverage=None 
                            ))
        except Exception as e:
            logger.error(f"Hyperliquid fetch error: {e}")
            
        return positions
