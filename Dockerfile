FROM python:3.11-slim

WORKDIR /app

# Unbuffer stdout/stderr for MCP stdio transport
ENV PYTHONUNBUFFERED=1

# Install dependencies first for layer caching
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy source
COPY src/ src/

# MCP uses stdio — no EXPOSE needed

ENTRYPOINT ["python", "-m", "src.server"]
