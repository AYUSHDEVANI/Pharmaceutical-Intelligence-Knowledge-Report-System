"""
MCP API Standard — Universal Schemas
=====================================
Pydantic v2 models defining the universal request/response envelope
that every PIKRS MCP server must follow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class DrugIdentifiers(BaseModel):
    """Pre-resolved identifiers to skip name-based lookup."""

    pubchem_cid: Optional[int] = None
    rxnorm_cui: Optional[str] = None
    cas_number: Optional[str] = None
    unii: Optional[str] = None
    drugbank_id: Optional[str] = None


class QueryOptions(BaseModel):
    """Optional query-tuning parameters."""

    timeout: int = Field(default=30, ge=1, le=120, description="Max seconds to wait for upstream")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    include_raw: bool = Field(default=False, description="Include raw upstream response for debugging")


class MCPRequest(BaseModel):
    """Universal MCP request — every server accepts this schema."""

    drug_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Common or generic name of the medicine",
    )
    identifiers: Optional[DrugIdentifiers] = Field(default=None, description="Pre-resolved drug identifiers")
    fields: Optional[list[str]] = Field(default=None, description="Filter: return only these result keys")
    options: QueryOptions = Field(default_factory=QueryOptions)
    request_id: Optional[str] = Field(default=None, description="Client-provided trace ID (echoed back)")

    @field_validator("drug_name")
    @classmethod
    def sanitize_drug_name(cls, v: str) -> str:
        """Strip whitespace and reject names with suspicious characters."""
        v = v.strip()
        if not v:
            raise ValueError("drug_name must not be blank")
        # Allow letters, digits, spaces, hyphens, parentheses, commas, periods
        allowed = set(
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789 -(),.'+"
        )
        if not all(c in allowed for c in v):
            raise ValueError(
                "drug_name contains invalid characters. "
                "Only alphanumeric, spaces, hyphens, parentheses, commas, periods, and apostrophes are allowed."
            )
        return v

    def effective_request_id(self) -> str:
        """Return the client-provided request_id or generate one."""
        return self.request_id or str(uuid4())


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class SourceInfo(BaseModel):
    """Identifies the upstream data source."""

    source_id: str = Field(..., description="Machine-readable key, e.g. 'pubchem'")
    name: str = Field(..., description="Human-readable source name, e.g. 'PubChem'")
    url: str = Field(..., description="Base URL of the upstream source")
    query_url: Optional[str] = Field(default=None, description="Exact URL queried")
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResponseMetadata(BaseModel):
    """Metadata attached to every MCP response."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    response_time_ms: float = Field(default=0.0, description="Server-side processing time")
    server_version: str = Field(default="1.0.0")
    result_count: int = Field(default=0)
    cached: bool = Field(default=False)


class MCPResponseData(BaseModel):
    """The data payload of a successful response."""

    drug_name: str
    identifiers: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)


class MCPResponse(BaseModel):
    """Universal success response envelope."""

    status: str = Field(default="success")
    source: SourceInfo
    data: MCPResponseData
    metadata: ResponseMetadata
    raw: Optional[dict[str, Any]] = Field(default=None, description="Raw upstream data (if requested)")


# ---------------------------------------------------------------------------
# Error response models
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Structured error information."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict)
    retry_after: Optional[float] = Field(default=None, description="Seconds to wait before retrying")


class MCPErrorResponse(BaseModel):
    """Universal error response envelope."""

    status: str = Field(default="error")
    source: Optional[SourceInfo] = None
    error: ErrorDetail
    metadata: ResponseMetadata


# ---------------------------------------------------------------------------
# Health check models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Returned by GET /health."""

    status: str = Field(default="healthy")
    source_id: str
    name: str
    version: str
    uptime_seconds: float = Field(default=0.0)
    upstream_reachable: bool = Field(default=True)
