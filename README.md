# 💊 PIKRS — Pharmaceutical Intelligence & Knowledge Report System

> **Real-time, AI-powered drug intelligence platform built on the Model Context Protocol (MCP)**

PIKRS aggregates structured pharmaceutical data from **7 authoritative public APIs** in parallel, normalizes it into a unified drug profile, and synthesizes actionable insights using large language models — all through a clean, extensible microservice architecture.

---

## ✨ Key Features

- **Multi-Source Real-Time Aggregation** — Queries PubChem, RxNorm, OpenFDA, ClinicalTrials.gov, PubMed, ChEMBL, and KEGG simultaneously
- **MCP-Native Architecture** — Each data source is an independent MCP server exposing tools via the official Python SDK
- **Parallel Async Orchestration** — All 7 servers execute concurrently using `asyncio.gather` with graceful failure isolation
- **AI-Powered Insights** — LLM providers (Groq / OpenAI) generate chemistry, pharmacology, and safety analysis from structured data
- **Extensible Plugin Design** — Add a new pharmaceutical data source by creating one folder and one config entry
- **Claude Desktop Compatible** — Every MCP server works directly with Claude via `stdio` transport

---

## 🏗️ System Architecture

```
                    ┌──────────────┐
                    │   User /     │
                    │   Client     │
                    └──────┬───────┘
                           │  HTTP POST
                           ▼
                    ┌──────────────┐
                    │   FastAPI    │
                    │ Orchestrator │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  MCP Client  │
                    │  (stdio)     │
                    └──────┬───────┘
                           │  asyncio.gather (parallel)
          ┌────────┬───────┼───────┬────────┬────────┐
          ▼        ▼       ▼       ▼        ▼        ▼
       ┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐┌──────┐
       │ChEMBL││PubChem││RxNorm││OpenFDA││Trials││PubMed││ KEGG │
       └──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘└──┬───┘
          │       │       │       │       │       │       │
          └───────┴───────┴───┬───┴───────┴───────┴───────┘
                              ▼
                    ┌──────────────┐
                    │  Aggregator  │
                    │+ Normalizer  │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │  AI Engine   │
                    │  (Groq/GPT)  │
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │   Drug       │
                    │   Report     │
                    └──────────────┘
```

### How MCP Works Here

The **Model Context Protocol (MCP)** is an open standard for connecting AI systems with external tools and data sources. Each PIKRS data source runs as an independent MCP server process that:

1. Starts as a subprocess via `stdio` transport
2. Performs a protocol handshake (`initialize`)
3. Exposes callable tools via `@mcp.tool()` decorators
4. Returns structured JSON results
5. Exits cleanly after each query

The orchestrator dynamically spawns, queries, and tears down MCP sessions — no persistent HTTP servers required.

---

## 📁 Project Structure

```
pharma/
├── orchestrator/                    # Central FastAPI orchestration layer
│   ├── main.py                      # FastAPI app + API endpoints
│   ├── service.py                   # generate_drug_profile() entrypoint
│   ├── mcp_client.py                # MCP stdio client (parallel tool calls)
│   ├── config.py                    # Dynamic MCP server registry
│   ├── aggregator.py                # Merges MCP responses → DrugProfile
│   ├── normalizer.py                # Cleans and deduplicates data
│   ├── models.py                    # Pydantic schemas (DrugProfile, etc.)
│   └── ai_engine/                   # AI Insight Engine
│       ├── service.py               # AI synthesis orchestration
│       ├── generator.py             # Report generation pipeline
│       ├── prompt.py                # LLM prompt templates
│       ├── config.py                # API keys + model settings (.env)
│       ├── models.py                # DrugIntelligenceReport schema
│       └── providers/               # LLM provider implementations
│           ├── groq_provider.py     # Groq (Llama 3.1)
│           └── base_provider.py     # Abstract LLM interface
│
├── mcp_servers/                     # Independent MCP server modules
│   ├── shared/                      # Shared utilities
│   │   ├── http_client.py           # Reusable async httpx wrapper
│   │   └── exceptions.py            # Unified error classes
│   ├── chembl/                      # EBI ChEMBL server
│   ├── pubchem/                     # NIH PubChem server
│   ├── rxnorm/                      # NLM RxNorm server
│   ├── openfda/                     # FDA drug label server
│   ├── clinicaltrials/              # ClinicalTrials.gov server
│   ├── pubmed/                      # NCBI PubMed server
│   └── kegg/                        # KEGG drug database server
```

Each MCP server follows an identical internal structure:

```
server_name/
├── client/
│   └── api_client.py     # Pure httpx API interaction logic
├── tools/
│   └── tool_name.py      # @mcp.tool() definitions
├── config.py              # Pydantic settings (base URL, timeout)
├── server.py              # FastMCP instance + tool registration
└── main.py                # stdio entrypoint
```

---

## 🔌 MCP Servers

Each MCP server is a self-contained Python service that wraps a public pharmaceutical API and exposes it as callable MCP tools.

### Available Servers & Tools

| Server | Tool Name | Data Source | Returns |
|--------|-----------|-------------|---------|
| **chembl** | `chembl_search` | EBI ChEMBL | Classification, approval, targets, molecular properties |
| **chembl** | `chembl_targets` | EBI ChEMBL | Mechanism-of-action targets |
| **pubchem** | `pubchem_search` | NIH PubChem | Formula, weight, SMILES, InChI, IUPAC name |
| **rxnorm** | `rxnorm_search` | NLM RxNav | RxCUI, ingredients, brand names, synonyms |
| **openfda** | `openfda_search` | FDA Labels | Indications, dosage, warnings, interactions |
| **clinicaltrials** | `clinicaltrials_search` | ClinicalTrials.gov | Trial title, status, phase, conditions |
| **pubmed** | `pubmed_search` | NCBI E-utilities | Paper titles, journals, publication years |
| **kegg** | `kegg_search` | KEGG REST | Drug IDs and descriptions |
| *All* | `health_check` | — | Upstream API connectivity status |

### How Tools Are Defined

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("chembl")

@mcp.tool()
async def chembl_search(drug_name: str) -> dict:
    """Search drug information from ChEMBL."""
    return await client.search_molecule(drug_name)
```

### Adding a New MCP Server

1. Create a new folder under `mcp_servers/your_source/`
2. Implement `client/api_client.py` with your API logic
3. Define tools in `tools/your_tool.py` using `@mcp.tool()`
4. Create `server.py`, `config.py`, and `main.py` (copy from any existing server)
5. Add one entry to `orchestrator/config.py`:

```python
"your_source": {
    "command": ["python", os.path.join(MCP_SERVERS_ROOT, "your_source", "main.py")],
    "tool": "your_tool_name",
    "timeout": 20,
},
```

That's it. The orchestrator will automatically query it on the next request.

---

## 🎯 Orchestrator

The orchestrator is the central coordination layer that ties everything together.

### Dynamic MCP Client (`mcp_client.py`)

- Reads the server registry from `config.py`
- Launches each MCP server as a subprocess via `stdio` transport
- Performs the MCP protocol handshake (`session.initialize()`)
- Calls the registered tool with `session.call_tool(tool_name, args)`
- Wraps results in the standardized envelope format for the aggregator

### Parallel Execution

All 7 MCP servers execute concurrently:

```python
tasks = [
    call_mcp_server(source_id, config, drug_name)
    for source_id, config in MCP_SERVERS.items()
]
completed = await asyncio.gather(*tasks, return_exceptions=True)
```

If one server fails (timeout, API error, network issue), the others continue unaffected. Only successful results are passed downstream.

### Aggregation & Normalization

- **Aggregator** maps each source's response fields into the unified `DrugProfile` schema
- **Normalizer** deduplicates synonyms, cleans whitespace, and standardizes formatting

---

## 🧠 AI Engine

The AI engine transforms raw structured data into human-readable intelligence reports.

### Analysis Domains

| Domain | What It Covers |
|--------|----------------|
| **Chemical Intelligence** | Molecular structure interpretation, SMILES analysis, druglikeness assessment |
| **Pharmacology** | Mechanism of action, target analysis, therapeutic classification |
| **Safety Profile** | Risk assessment, black box warnings, contraindication severity |
| **Overview** | Executive summary synthesizing all domains |

### LLM Providers

The engine supports pluggable LLM providers:

- **Groq** (default) — Llama 3.1 70B via Groq Cloud (fast inference)
- **OpenAI** — GPT-4o Mini (fallback option)

Configuration is managed via `.env` files with Pydantic Settings.

---

## ⚙️ Installation

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- A **Groq API key** (free at [console.groq.com](https://console.groq.com))

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/pikrs.git
cd pikrs

# Install dependencies
pip install -r orchestrator/requirements.txt

# Configure AI engine
cp orchestrator/ai_engine/.env.example orchestrator/ai_engine/.env
# Edit the .env file and add your GROQ_API_KEY
```

### Core Dependencies

```
fastapi          # Web framework
uvicorn          # ASGI server
mcp              # Model Context Protocol SDK
httpx             # Async HTTP client (used inside MCP servers)
pydantic         # Data validation
pydantic-settings # Environment configuration
langchain-groq   # LLM provider
```

---

## 🚀 Running the System

### Start the Orchestrator

The orchestrator automatically spawns MCP servers on-demand — you don't need to start them manually.

```bash
cd pharma
uvicorn orchestrator.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Test Individual MCP Servers (Optional)

You can test any MCP server independently using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector python mcp_servers/chembl/main.py
```

---

## 📡 API Usage

### `POST /profile` — Raw Drug Profile

Returns structured data aggregated from all 7 sources.

```bash
curl -X POST http://127.0.0.1:8000/profile \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "ibuprofen"}'
```

### `POST /intelligence` — AI-Enhanced Report

Returns structured data **plus** AI-generated insights (chemistry, pharmacology, safety).

```bash
curl -X POST http://127.0.0.1:8000/intelligence \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "ibuprofen"}'
```

### `GET /health` — Health Check

```bash
curl http://127.0.0.1:8000/health
```

---

## 🖥️ Claude Desktop Integration

Each MCP server can be connected directly to Claude Desktop for interactive tool usage.

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "chembl": {
      "command": "python",
      "args": ["C:/path/to/pharma/mcp_servers/chembl/main.py"]
    },
    "pubchem": {
      "command": "python",
      "args": ["C:/path/to/pharma/mcp_servers/pubchem/main.py"]
    },
    "rxnorm": {
      "command": "python",
      "args": ["C:/path/to/pharma/mcp_servers/rxnorm/main.py"]
    },
    "openfda": {
      "command": "python",
      "args": ["C:/path/to/pharma/mcp_servers/openfda/main.py"]
    },
    "clinicaltrials": {
      "command": "python",
      "args": ["C:/path/to/pharma/mcp_servers/clinicaltrials/main.py"]
    },
    "kegg": {
      "command": "python",
      "args": ["C:/path/to/pharma/mcp_servers/kegg/main.py"]
    },
    "pubmed": {
      "command": "python",
      "args": ["C:/path/to/pharma/mcp_servers/pubmed/main.py"]
    }
  }
}
```

After restarting Claude Desktop, you can ask Claude to search across all pharmaceutical databases interactively.

---

## 📋 Example Output

### `POST /profile` Response (Truncated)

```json
{
  "drug_name": "ibuprofen",
  "identifiers": {
    "rxnorm_cui": "5640",
    "pubchem_cid": 3672,
    "chembl_id": "CHEMBL521"
  },
  "chemical_properties": {
    "molecular_formula": "C13H18O2",
    "molecular_weight": 206.28,
    "iupac_name": "2-(4-isobutylphenyl)propanoic acid",
    "canonical_smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O"
  },
  "regulatory_information": {
    "indications": "For relief of mild to moderate pain...",
    "dosage": "200-400mg every 4-6 hours...",
    "warnings": "Cardiovascular risk, GI bleeding...",
    "contraindications": "Known hypersensitivity to NSAIDs...",
    "adverse_reactions": "Nausea, dyspepsia, dizziness...",
    "drug_interactions": "Anticoagulants, ACE inhibitors..."
  },
  "chembl": {
    "chembl_id": "CHEMBL521",
    "classification": { "drug_type": "Small molecule" },
    "targets": [
      {
        "target_name": "Cyclooxygenase-2",
        "mechanism": "Cyclooxygenase inhibitor"
      }
    ]
  },
  "clinical_trials": [
    {
      "title": "Ibuprofen vs Acetaminophen for Pain Management",
      "status": "RECRUITING",
      "phase": "Phase 3"
    }
  ],
  "research_papers": [
    {
      "title": "Anti-inflammatory mechanisms of ibuprofen",
      "journal": "Journal of Pharmacology",
      "year": "2024"
    }
  ],
  "brand_names": ["Advil", "Motrin", "Nurofen"],
  "synonyms": ["ibuprofen", "Ibuprofenum"],
  "sources": ["pubchem", "rxnorm", "openfda", "clinicaltrials", "pubmed", "chembl", "kegg"]
}
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | FastAPI + Uvicorn |
| **Protocol** | MCP (Model Context Protocol) via FastMCP |
| **Transport** | stdio (subprocess-based) |
| **HTTP Client** | httpx (async, inside MCP servers) |
| **Data Validation** | Pydantic v2 |
| **Configuration** | pydantic-settings + `.env` files |
| **Concurrency** | Python asyncio |
| **LLM Providers** | Groq (Llama 3.1), OpenAI (GPT-4o) |
| **Language** | Python 3.10+ |

---

## 🔮 Future Enhancements

- **Redis Caching** — Cache MCP responses to reduce API calls for repeated drug queries
- **Persistent MCP Sessions** — Connection pooling for long-lived MCP server processes
- **Knowledge Graph** — Build a Neo4j-backed drug interaction and similarity graph
- **Distributed Orchestration** — Scale across multiple nodes using Celery or Ray
- **Autonomous Agent Selection** — Let the LLM dynamically choose which MCP tools to call based on the query context
- **Streaming Responses** — Real-time progress updates as each MCP server returns data
- **Authentication & Rate Limiting** — API key management and per-user query quotas
- **Web Dashboard** — Streamlit or React-based frontend for interactive drug exploration

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ for pharmaceutical intelligence
</p>
