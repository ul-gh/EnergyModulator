#!/usr/bin/env python3
"""Run Energy Modulator Server.

See documentation in README.md.
"""

import argparse
import logging
import sys

from energy_modulator.server import EnergyModulatorServer

parser = argparse.ArgumentParser(prog=__package__, description=__doc__)
_ = parser.add_argument("-v", "--verbose", action="store_true", help="Set loglevel to DEBUG")
_ = parser.add_argument("-q", "--quiet", action="store_true", help="Set loglevel to WARNING")
_ = parser.add_argument("-d", "--daemon", action="store_true", help="Run in background thread with task supervision.")
_ = parser.add_argument("--datalog", action="store_true", help="Activate logging of measurement data.")
cmdline = parser.parse_args()


if cmdline.verbose:  # pyright: ignore[reportAny]
    logging.basicConfig(level=logging.DEBUG)
elif cmdline.quiet:  # pyright: ignore[reportAny]
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.INFO)


energy_modulator = EnergyModulatorServer(cmdline)


def main() -> None:
    """Run Energy Modulator Server."""
    try:
        if cmdline.daemon:
            energy_modulator.run_threaded()
        else:
            energy_modulator.run()
        # Server thread or task should never terminate.
        sys.exit(1)
    except KeyboardInterrupt:
        # Suppress sys.exit() when running interactively.
        energy_modulator.stop()
        if "get_ipython" not in locals():
            sys.exit(0)


if __name__ == "__main__":
    main()
