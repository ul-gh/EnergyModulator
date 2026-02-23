#!/usr/bin/env python3
# pyright: reportAny=false
"""Run Energy Modulator Server.

See documentation in README.md.
"""

import argparse
import asyncio
import logging
import sys
from threading import Thread

from energy_modulator.server import EnergyModulatorServer

parser = argparse.ArgumentParser(prog=__package__, description=__doc__)
_ = parser.add_argument("-v", "--verbose", action="store_true", help="Set loglevel to DEBUG")
_ = parser.add_argument("-q", "--quiet", action="store_true", help="Set loglevel to WARNING")
_ = parser.add_argument("-d", "--daemon", action="store_true", help="Run in background thread with task supervision.")
_ = parser.add_argument("--datalog", action="store_true", help="Activate logging of measurement data.")
cmdline = parser.parse_args()


if cmdline.verbose:
    logging.basicConfig(level=logging.DEBUG)
elif cmdline.quiet:
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("EnergyModulator")


class EnergyModulator:
    """Energy Modulator Application."""

    server: EnergyModulatorServer | None = None
    thread: Thread | None = None

    def run(self) -> None:
        """Run EnergyModulator on asyncio event loop."""
        asyncio.run(self._run_server())

    def run_threaded(self) -> None:
        """Run EnergyModulator in new background thread."""
        self.thread = Thread(target=self.run, name="energy_modulator", daemon=False)
        self.thread.start()
        logger.info("EnergyModulator running in thread: %s", self.thread)

    def stop(self) -> None:
        """Cancel all EnergyModulator tasks."""
        logger.info("EnergyModulator.stop() called..")
        if self.server is not None:
            self.server.stop()
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    def main(self) -> None:
        """Run Energy Modulator from command line."""
        if cmdline.daemon:
            self.run_threaded()
        else:
            self.run()
            # Non-threaded task should never terminate.
            sys.exit(1)

    async def _run_server(self) -> None:
        """Run all server tasks."""
        self.server = EnergyModulatorServer(datalog_enabled=cmdline.datalog_enabled)
        await self.server.run_forever()


if __name__ == "__main__":
    energy_modulator = EnergyModulator()
    try:
        energy_modulator.main()
    except KeyboardInterrupt:
        # Suppress sys.exit() when running interactively.
        energy_modulator.stop()
        if "get_ipython" not in locals():
            sys.exit(0)
