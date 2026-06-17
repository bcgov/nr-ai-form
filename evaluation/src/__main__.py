"""
__main__.py - Module entry point for running evaluation via python -m
"""

import asyncio
import sys
import argparse
from src.main import main, EvaluationRunner

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
