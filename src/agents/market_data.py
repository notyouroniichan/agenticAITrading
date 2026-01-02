import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import List, Dict, Callable, Optional
import duckdb
from src.models.schema import MarketTicker, init_duckdb
from src.core.config import settings

logger = logging.getLogger(__name__)

class MarketDataAgent:
    def __init__(self, db_path: str = "market_data.duckdb"):
        self.duck_conn = init_duckdb(db_path)
        self.running = False
        self.tasks = []
        
    async def start(self):
        """Start ingesting data from configured exchanges."""
        self.running = True
        logger.info("Starting Market Data Agent...")
        
        # Add exchange connectors here
        self.tasks.append(asyncio.create_task(self._connect_binance(["btcusdt", "ethusdt"])))
        self.tasks.append(asyncio.create_task(self._connect_hyperliquid()))
        
        try:
            await asyncio.gather(*self.tasks)
        except Exception as e:
            logger.error(f"Market Data Agent crashed: {e}")
            
    async def stop(self):
        self.running = False
        for task in self.tasks:
            task.cancel()
        logger.info("Market Data Agent stopped.")

    async def _parameterized_persist(self, ticker: MarketTicker):
        """Persist ticker to DuckDB."""
        try:
             self.duck_conn.execute(
                "INSERT INTO market_ticks VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    ticker.venue, 
                    ticker.symbol, 
                    ticker.timestamp, 
                    ticker.bid, 
                    ticker.ask, 
                    ticker.last, 
                    ticker.volume_24h
                )
            )
        except Exception as e:
            logger.error(f"Failed to persist ticker: {e}")

    async def _connect_binance(self, symbols: List[str]):
        """Connect to Binance WebSocket for multiple symbols."""
        streams = "/".join([f"{s}@ticker" for s in symbols])
        url = f"wss://stream.binance.com:9443/ws/{streams}"
        
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    logger.info(f"Connected to Binance WS for {symbols}")
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        # Normalize
                        ticker = MarketTicker(
                            venue="binance",
                            symbol=data['s'], # Symbol e.g. BTCUSDT
                            timestamp=datetime.fromtimestamp(data['E'] / 1000),
                            bid=float(data['b']),
                            ask=float(data['a']),
                            last=float(data['c']),
                            volume_24h=float(data['v'])
                        )
                        
                        await self._parameterized_persist(ticker)
                        logger.debug(f"Binance Tick: {ticker.symbol} ${ticker.last}")
                        
            except Exception as e:
                logger.error(f"Binance WS connection error: {e}")
                await asyncio.sleep(5)

    async def _connect_hyperliquid(self):
        """Connect to Hyperliquid WebSocket (Mainnet)."""
        url = "wss://api.hyperliquid.xyz/ws"
        
        while self.running:
            try:
                async with websockets.connect(url) as ws:
                    logger.info("Connected to Hyperliquid WS")
                    
                    # Subscribe to all mids (tickers)
                    sub_msg = {
                        "method": "subscribe",
                        "subscription": {"type": "allMids"}
                    }
                    await ws.send(json.dumps(sub_msg))
                    
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        if data.get("channel") == "allMids":
                            mids = data.get("data", {}).get("mids", {})
                            ts = datetime.now() # Hyperliquid allMids doesn't send TS per tick, use local
                            
                            for symbol, price in mids.items():
                                # Hyperliquid mids only gives mid price, not full depth here.
                                # Approximating last/bid/ask as mid for this snapshot feed
                                price_f = float(price)
                                ticker = MarketTicker(
                                    venue="hyperliquid",
                                    symbol=symbol,
                                    timestamp=ts,
                                    bid=price_f,
                                    ask=price_f,
                                    last=price_f,
                                    volume_24h=0.0 # Not provided in allMids
                                )
                                await self._parameterized_persist(ticker)
                                
            except Exception as e:
                logger.error(f"Hyperliquid WS connection error: {e}")
                await asyncio.sleep(5)
