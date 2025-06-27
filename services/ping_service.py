import asyncio
import os
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ping_service")

# Load server URL from .env file
load_dotenv()
PING_URL = os.getenv("RENDER_EXTERNAL_URL")

# Ping interval in seconds. 10 minutes (600s)
PING_INTERVAL_SECONDS = 10 * 60


async def run_ping():
    """
    An async task that runs forever, pinging the server's root URL periodically.
    """
    logger.info(f"Ping Service started. Will ping {PING_URL} every {PING_INTERVAL_SECONDS} seconds.")

    while True:
        try:
            # Sleep first, so it doesn't ping immediately on startup.
            await asyncio.sleep(PING_INTERVAL_SECONDS)

            async with httpx.AsyncClient(timeout=30) as client:
                logger.info(f"[{datetime.now(timezone.utc).isoformat()}] Ping: Waking up to ping server...")
                response = await client.get(PING_URL)
                response.raise_for_status()

            logger.info(f"Ping: Successfully pinged server. Status code: {response.status_code}")

        except asyncio.CancelledError:
            logger.info("Ping task is being cancelled. Shutting down gracefully.")
            break
        except httpx.RequestError as e:
            logger.warning(f"Ping Error: An error occurred while pinging {e.request.url!r}.")
        except httpx.HTTPStatusError as e:
            logger.warning(f"Ping Error: Received status code {e.response.status_code} for {e.request.url!r}.")
        except Exception as e:
            logger.warning(f"An unexpected error occurred in the Pinger task: {e}")