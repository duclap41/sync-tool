from __future__ import annotations

import traceback

from ui import MainWindow


def main():

    try:

        app = MainWindow()

        app.run()

    except KeyboardInterrupt:

        print("Exiting...")

    except Exception:

        print("=" * 80)

        print("Fatal Error")

        print("=" * 80)

        traceback.print_exc()

        input("\nPress ENTER to exit...")


if __name__ == "__main__":

    main()