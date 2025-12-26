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

from energy_modulator.server import EnergyModulatorServer

parser = argparse.ArgumentParser(prog=__package__, description=__doc__)
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Set loglevel to DEBUG")
parser.add_argument("-q", "--quiet", action="store_true",
                    help="Set loglevel to WARNING")
parser.add_argument("-d", "--daemon", action="store_true",
                    help="Run in background thread with task supervision.")
cmdline = parser.parse_args()


logger = logging.getLogger(__name__)
if cmdline.verbose:
    logging.basicConfig(level=logging.DEBUG)
elif cmdline.quiet:
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)


app: EnergyModulatorServer
main_thread: threading.Thread


def run_server() -> None:
    """Run app in foreground (also as a system service)."""
    global app
    app = EnergyModulatorServer()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        # Suppress sys.exit() when running interactively.
        if "get_ipython" not in locals():
            sys.exit(0)
    except Exception:  # noqa: BLE001
        # Main task should never terminate.
        sys.exit(1)


def start() -> None:
    """Run app in new background thread."""
    global main_thread
    main_thread = threading.Thread(target=run_server, name="energy_modulator", daemon=False)
    main_thread.start()
    logger.info("App running in background thread: %s", main_thread)


def stop() -> None:
    """Stop app."""
    main_thread.join()
    logger.info("Stopped app running in thread: %s", main_thread)


def main():
    """Run Energy Modulator Server."""
    if cmdline.daemon:
        logger.info("Starting Energy Modulator Server in background thread.")
        start()
    else:
        logger.info("Starting Energy Modulator Server")
        run_server()


if __name__ == "__main__":
    main()
