"""Allow the framework to be run as a module: python -m wildguard_framework"""
import os
import sys

_framework_dir = os.path.dirname(os.path.abspath(__file__))
if _framework_dir not in sys.path:
    sys.path.insert(0, _framework_dir)

from main import main  # noqa: E402

if __name__ == "__main__":
    main()
