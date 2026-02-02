#!/usr/bin/env python3
# ruff: noqa: PLW0603
"""Run Energy Modulator Server.

See documentation in README.md.
"""
import argparse
import asyncio
import logging
import sys
import threading
from collections.abc import Coroutine
from typing import Any

from energy_modulator.server import EnergyModulatorServer

parser = argparse.ArgumentParser(prog=__package__, description=__doc__)
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Set loglevel to DEBUG")
parser.add_argument("-q", "--quiet", action="store_true",
                    help="Set loglevel to WARNING")
parser.add_argument("-d", "--daemon", action="store_true",
                    help="Run in background thread with task supervision.")
parser.add_argument("--datalog", action="store_true",
                    help="Activate logging of measurement data.")
cmdline = parser.parse_args()


if cmdline.verbose:
    logging.basicConfig(level=logging.DEBUG)
elif cmdline.quiet:
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)


logger = logging.getLogger("energy_modulator:main")
server: EnergyModulatorServer
main_thread: threading.Thread


def wait_for(coro: Coroutine[Any, Any, object]) -> object:
    """Run coroutine on the server event loop and return the result.

    Intended for diagnostics and debugging use when running in a REPL (IPython).
    """
    future = asyncio.run_coroutine_threadsafe(coro, server.loop)
    return future.result()


def run_server() -> None:
    """Run app in foreground (also as a system service)."""
    global server
    with EnergyModulatorServer(cmdline) as server:
        asyncio.run(server.run_forever())


def start() -> None:
    """Run app in new background thread."""
    global main_thread
    main_thread = threading.Thread(target=run_server, name="energy_modulator", daemon=False)
    main_thread.start()
    logger.info("App running in thread: %s", main_thread)


def stop() -> None:
    """Stop energy_modulator app."""
    logger.info("stop() called..")
    server.stop()
    main_thread.join()


def main() -> None:
    """Run Energy Modulator Server."""
    try:
        if cmdline.daemon:
            logger.info("Starting Energy Modulator Server in background thread.")
            start()
        else:
            logger.info("Starting Energy Modulator Server")
            run_server()
    except KeyboardInterrupt:
        # Suppress sys.exit() when running interactively.
        stop()
        if "get_ipython" not in locals():
            sys.exit(0)
    except Exception:
        # Main task should never terminate.
        logger.exception("Exception in main()!")
        stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
