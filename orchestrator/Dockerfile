# ==========================================
# PIKRS Orchestrator Dockerfile
# ==========================================
# Acts as the AI Insight engine and MCP Client hub.
FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Install dependencies first for layer caching
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the orchestrator module
COPY orchestrator/ /app/orchestrator/

# We also need the shared library for the underlying models
COPY mcp-servers/shared/ /app/shared/

# Set Python path so it can find orchestrator and shared
ENV PYTHONPATH=/app

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the API port
EXPOSE 8000

# The orchestrator will serve a FastAPI app (to be created next)
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]
