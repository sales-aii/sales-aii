#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sales.aii - Main entry point
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.logger import logger


def main():
    """Main application entry point"""
    try:
        logger.info("Sales.aii starting...")
        # Start UI
        from ui.app import run_ui
        run_ui()
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
