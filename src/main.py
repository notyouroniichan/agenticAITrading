import asyncio
import logging
from src.core.config import settings
from src.core.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Agentic Portfolio Analytics System...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down system...")

if __name__ == "__main__":
    asyncio.run(main())
