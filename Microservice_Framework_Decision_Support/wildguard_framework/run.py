"""Wrapper: equivalent to `python main.py` (kept for backward compatibility)."""
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from main import main  # noqa: E402

if __name__ == "__main__":
    main()
