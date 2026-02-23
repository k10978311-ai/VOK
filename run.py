"""Run the app from project root: python run.py or uv run run.py"""
import sys
from pathlib import Path

# Ensure project root is on path when running run.py directly
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
