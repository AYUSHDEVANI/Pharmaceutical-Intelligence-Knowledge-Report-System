# RxNorm MCP Server

**PIKRS** — Pharmaceutical Intelligence & Knowledge Report System

MCP server for [RxNorm](https://lhncbc.nlm.nih.gov/RxNav/), a normalized naming system for clinical drugs maintained by the National Library of Medicine (NLM).

This server performs a two-step API process to resolve drug names into universal RxCUI identifiers and extract associated clinical concepts.

## Retrieved Data

| Field | Description |
|---|---|
| `rxnorm_cui` | RxNorm Concept Unique Identifier (RxCUI) |
| `ingredient_name` | The precise active ingredient name |
| `brand_names` | List of commercial brand names associated with the drug |
| `synonyms` | List of alternative clinical names and abbreviations |

## Quick Start

### 1. Install Dependencies

```bash
cd mcp-servers/rxnorm
pip install -r requirements.txt
```

### 2. Configure (Optional)

```bash
cp .env.example .env
```

### 3. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8101 --reload
```

### 4. Open Swagger Docs

Visit **http://localhost:8101/docs**

## Example Requests

### Query a Drug

```bash
curl -X POST http://localhost:8101/query \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "aspirin"}'
```

Returns RxCUI along with extracted ingredients, synonyms, and brand names.

### Health Check

```bash
curl http://localhost:8101/health
```

## Testing

```bash
cd mcp-servers/rxnorm
python -m pytest tests/ -v
```

## Docker

```bash
docker build -t pikrs-rxnorm .
docker run -p 8101:8101 pikrs-rxnorm
```
