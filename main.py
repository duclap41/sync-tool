from __future__ import annotations

from logger import get_logger
from ui import MainWindow

log = get_logger(__name__)


def main():

    log.info("=== Pokemon Save Sync starting ===")

    try:

        app = MainWindow()

        app.run()

        log.info("=== Exited normally ===")

    except KeyboardInterrupt:

        log.info("Interrupted by user (Ctrl+C). Exiting.")

    except Exception:

        log.exception("Fatal error")

        input("\nLog written to logs/sync.log. Press ENTER to exit...")


if __name__ == "__main__":

    main()