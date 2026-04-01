"""Entry point for running the Maki assistant application."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

from app.main import main


# TODO: Add command-line arguments for startup options later.
if __name__ == "__main__":
    raise SystemExit(main())
