# PubChem MCP Server

**PIKRS** — Pharmaceutical Intelligence & Knowledge Report System

MCP server for [PubChem](https://pubchem.ncbi.nlm.nih.gov), the world's largest free chemistry database. Retrieves compound properties via the PubChem PUG REST API.

## Retrieved Data

| Field | Description |
|---|---|
| `molecular_formula` | e.g. `C9H8O4` |
| `molecular_weight` | In g/mol |
| `iupac_name` | IUPAC systematic name |
| `canonical_smiles` | Canonical SMILES string |
| `inchi` | InChI identifier |
| `inchi_key` | InChIKey hash |
| `pubchem_cid` | PubChem Compound ID |

## Quick Start

### 1. Install Dependencies

```bash
cd mcp-servers/pubchem
pip install -r requirements.txt
```

### 2. Configure (Optional)

```bash
cp .env.example .env
# Edit .env if needed
```

### 3. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

### 4. Open Swagger Docs

Visit **http://localhost:8100/docs** for interactive API documentation.

## Example Requests

### Query a Drug

```bash
curl -X POST http://localhost:8100/query \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "aspirin"}'
```

### Query with Field Filter

```bash
curl -X POST http://localhost:8100/query \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "aspirin", "fields": ["molecular_formula", "molecular_weight"]}'
```

### Query by CID

```bash
curl -X POST http://localhost:8100/query \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "aspirin", "identifiers": {"pubchem_cid": 2244}}'
```

### Health Check

```bash
curl http://localhost:8100/health
```

## Testing

```bash
cd mcp-servers/pubchem
python -m pytest tests/ -v
```

## Docker

```bash
docker build -t pikrs-pubchem .
docker run -p 8100:8100 pikrs-pubchem
```

## Architecture

```
pubchem/
├── app/
│   ├── main.py          # FastAPI app factory
│   ├── config.py        # Environment-driven settings
│   ├── connector.py     # PubChem REST API connector
│   ├── router.py        # POST /query, GET /health
│   └── models.py        # PubChem-specific Pydantic models
├── tests/
│   ├── test_connector.py
│   └── test_router.py
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

This server depends on the shared library at `mcp-servers/shared/`.
