import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uniprot.server import mcp

if __name__ == "__main__":
    mcp.run(transport = "stdio")