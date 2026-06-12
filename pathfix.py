"""
pathfix.py — Ensures the project root is always on sys.path.
Every module that uses bare imports (from models import ...) must
import this first: import pathfix  # noqa
"""
import sys
import os

# Add the project root (the folder containing this file) to sys.path
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
