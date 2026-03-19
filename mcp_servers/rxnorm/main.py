#!/usr/bin/env python3
"""RxNorm MCP Server — stdio entrypoint."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rxnorm.server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
