# opencode MCP Configuration Backup
# Location: ~/.config/opencode/opencode.jsonc
# Add the "india-market" entry to your "mcp" section:

```json
"india-market": {
  "type": "local",
  "command": ["docker", "run", "-i", "--rm", "india-market-mcp"]
}
```

## Setup Steps

### 1. Build the Docker image (one-time)
```bash
cd india-market-mcp
docker build -t india-market-mcp .
```

### 2. Add to opencode config
Edit `~/.config/opencode/opencode.jsonc` and add the `india-market` entry under `"mcp"`.

### 3. Restart opencode
The 60 India market tools will be available automatically.

## Alternative: Run without Docker
```bash
pip install -e .
# Then add to opencode config:
# "command": ["python", "-m", "src.server"]
# "cwd": "D:\\Default Project\\nse-mcp-servers\\india-market-mcp"
```
