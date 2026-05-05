FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Assemble the ros_mcp package then install entry-point (ros-msp)
COPY pyproject.toml .
COPY __init__.py main.py integration.py ./ros_mcp/
COPY tools/    ./ros_mcp/tools/
COPY utils/    ./ros_mcp/utils/
COPY resources/ ./ros_mcp/resources/
COPY prompts/  ./ros_mcp/prompts/
RUN pip install --no-cache-dir --no-deps .

EXPOSE 8000

# FastMCP sse transport → SSE endpoint at /sse  (no /health route)
# TCP port check is used instead of HTTP for healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('localhost',8000),2); s.close()" || exit 1

# rosbridge connection is configured via ROSBRIDGE_IP / ROSBRIDGE_PORT env vars
CMD ["ros-msp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
