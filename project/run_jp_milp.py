"""Run from any working directory; see model/jp_milp_implementation.md."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.jp_milp.cli import main

if __name__ == '__main__':
    raise SystemExit(main())
