#!/usr/bin/env python3
"""Wrapper that can be run from any directory: equivalent to `python main.py`."""
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

if __name__ == "__main__":
    from main import main
    main()
