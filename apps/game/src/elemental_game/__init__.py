from pathlib import Path

try:
    __version__ = Path(__file__).with_name("VERSION").read_text().strip()
except FileNotFoundError:
    __version__ = "0.0.0+dev"
