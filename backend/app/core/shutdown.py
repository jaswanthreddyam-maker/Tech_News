import asyncio
import logging
import signal

logger = logging.getLogger("tech_news.shutdown")

# Global event triggered when the application begins its shutdown lifespan phase
shutdown_event = asyncio.Event()


def register_signal_handlers():
    try:
        loop = asyncio.get_running_loop()

        def handle_signal(sig):
            logger.info(f"Signal {sig} caught: triggering clean shutdown for all active streams.")
            shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, lambda sig=sig: handle_signal(sig))
            except (NotImplementedError, RuntimeError):
                pass
    except Exception as e:
        logger.warning(f"Failed to register signal handlers: {e}")
