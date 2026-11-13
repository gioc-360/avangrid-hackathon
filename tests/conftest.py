"""Test setup: lets tests import repo code while Python runs with -I.

What: puts the repo root at the front of sys.path.
Why:  `python -I` drops the current directory from the import path, so `import analysis.facts` would fail.
How:  one sys.path insert, run by pytest before any test file is collected.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
