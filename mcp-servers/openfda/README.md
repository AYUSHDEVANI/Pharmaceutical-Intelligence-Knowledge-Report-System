# OpenFDA MCP Server

**PIKRS** — Pharmaceutical Intelligence & Knowledge Report System

MCP server for [OpenFDA](https://open.fda.gov/), retrieving regulatory and safety data including active warnings, dosage, and side effects.

This server queries the OpenFDA drug label endpoint based on generic names.

## Retrieved Data

| Field | Description |
|---|---|
| `indications` | Indications and usage |
| `dosage` | Dosage and administration instructions |
| `warnings` | Boxed warnings (prioritized) or general warnings |
| `contraindications` | Known contraindications |
| `adverse_reactions` | Adverse reactions and side effects |
| `drug_interactions` | Known drug interactions |

## Quick Start

### 1. Install Dependencies

```bash
cd mcp-servers/openfda
pip install -r requirements.txt
```

### 2. Configure (Optional)

```bash
cp .env.example .env
```

### 3. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8102 --reload
```

### 4. Open Swagger Docs

Visit **http://localhost:8102/docs**

## Example Requests

### Query a Drug Label

```bash
curl -X POST http://localhost:8102/query \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "aspirin"}'
```

Returns the structured OpenFDA label properties inside the standard MCP envelope.

## Testing

```bash
cd mcp-servers/openfda
python -m pytest tests/ -v
```

## Docker

```bash
docker build -t pikrs-openfda .
docker run -p 8102:8102 pikrs-openfda
```
