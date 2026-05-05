FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install package (entry-point: mission-control-mcp)
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

EXPOSE 8000

# Health-check hits the /health endpoint added in SSE mode
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# MCP_TRANSPORT=sse  →  SSE/HTTP server (default for containers)
# MCP_TRANSPORT=stdio →  stdio server (for local process spawning)
ENV MCP_TRANSPORT=sse \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

CMD ["mission-control-mcp"]
