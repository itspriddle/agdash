"""Entry point."""

from agdash.app import App
from agdash.services.config import Config


def main() -> None:
    config = Config.load()
    app = App(config)
    app.run()


if __name__ == "__main__":
    main()
