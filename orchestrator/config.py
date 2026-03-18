"""
PIKRS Orchestrator — Configuration
====================================
Dynamic MCP server registry using stdio subprocess commands.
To add a new data source, simply add a new entry below.
"""

from __future__ import annotations

import os

# Base configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))

# ---------------------------------------------------------------------------
# MCP Server Base Path
# ---------------------------------------------------------------------------
# All MCP servers live under this root directory.
MCP_SERVERS_ROOT = os.getenv(
    "MCP_SERVERS_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_servers"))
)

# ---------------------------------------------------------------------------
# Dynamic MCP Server Registry (stdio transport)
# ---------------------------------------------------------------------------
# Each entry maps a source_id to its startup command and tool name.
# The orchestrator will launch each server as a subprocess via stdio,
# call the specified tool, and collect the result.
#
# To add a new MCP server:
#   1. Create it under mcp_servers/<name>/
#   2. Add an entry here with its main.py path and tool name.
#   That's it. The orchestrator handles everything else automatically.

MCP_SERVERS = {
    "pubchem": {
        "command": ["python", os.path.join(MCP_SERVERS_ROOT, "pubchem", "main.py")],
        "tool": "pubchem_search",
        "timeout": int(os.getenv("PUBCHEM_TIMEOUT", "20")),
    },
    "rxnorm": {
        "command": ["python", os.path.join(MCP_SERVERS_ROOT, "rxnorm", "main.py")],
        "tool": "rxnorm_search",
        "timeout": int(os.getenv("RXNORM_TIMEOUT", "20")),
    },
    "openfda": {
        "command": ["python", os.path.join(MCP_SERVERS_ROOT, "openfda", "main.py")],
        "tool": "openfda_search",
        "timeout": int(os.getenv("OPENFDA_TIMEOUT", "20")),
    },
    "clinicaltrials": {
        "command": ["python", os.path.join(MCP_SERVERS_ROOT, "clinicaltrials", "main.py")],
        "tool": "clinicaltrials_search",
        "timeout": int(os.getenv("CLINICALTRIALS_TIMEOUT", "60")),
    },
    "pubmed": {
        "command": ["python", os.path.join(MCP_SERVERS_ROOT, "pubmed", "main.py")],
        "tool": "pubmed_search",
        "timeout": int(os.getenv("PUBMED_TIMEOUT", "50")),
    },
    "chembl": {
        "command": ["python", os.path.join(MCP_SERVERS_ROOT, "chembl", "main.py")],
        "tool": "chembl_search",
        "timeout": int(os.getenv("CHEMBL_TIMEOUT", "20")),
    },
    "kegg": {
        "command": ["python", os.path.join(MCP_SERVERS_ROOT, "kegg", "main.py")],
        "tool": "kegg_search",
        "timeout": int(os.getenv("KEGG_TIMEOUT", "20")),
    },
}
