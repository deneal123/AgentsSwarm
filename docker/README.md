# vLLM Service - Docker Deployment

This directory contains Docker configuration for deploying vLLM Service in Data Parallel mode.

## Quick Start

### 1. Choose Your Node

**Node 0 (Coordinator)** - First server:
```bash
cp .env.node0 .env
# Edit .env and set VLLM_DATA_PARALLEL_ADDRESS to this server's IP
./deploy.sh build
./deploy.sh up
```

**Node 1 (Worker)** - Second server:
```bash
cp .env.node1 .env
# Edit .env and set VLLM_DATA_PARALLEL_ADDRESS to Node 0's IP
./deploy.sh build
./deploy.sh up
```

### 2. Verify

```bash
# Check status
./deploy.sh status

# View logs
./deploy.sh logs

# Test API
curl http://localhost:8000/health
```

## Files

| File | Description |
|------|-------------|
| `Dockerfile` | Docker image with uv and vLLM |
| `docker-compose.yml` | Universal single-node deployment |
| `.env.node0` | Environment template for coordinator |
| `.env.node1` | Environment template for worker |
| `deploy.sh` | Deployment script (Linux/macOS) |
| `deploy.bat` | Deployment script (Windows) |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Data Parallel Cluster                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐         ┌──────────────────┐      │
│  │     Node 0       │         │     Node 1       │      │
│  │   Coordinator    │◄───────►│     Worker       │      │
│  │   (rank 0)       │  RPC    │   (rank 1)       │      │
│  │                  │         │                  │      │
│  │  V100 32GB       │         │  V100 32GB       │      │
│  │  Port: 8000      │         │  Port: 8000      │      │
│  └──────────────────┘         └──────────────────┘      │
│                                                          │
│  Each node runs independently with docker-compose        │
│  Nodes communicate via RPC for coordination              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Required Environment Variables

| Variable | Description | Node 0 | Node 1 |
|----------|-------------|--------|--------|
| `VLLM_DATA_PARALLEL_SIZE` | Total nodes | 2 | 2 |
| `VLLM_DATA_PARALLEL_RANK` | This node's rank | 0 | 1 |
| `VLLM_DATA_PARALLEL_ADDRESS` | Coordinator IP | This node's IP | Node 0's IP |
| `VLLM_DATA_PARALLEL_RPC_PORT` | RPC port | 13345 | 13345 |

### Network Requirements

- Both nodes must be able to reach each other via network
- RPC port (default: 13345) must be open between nodes
- API port (default: 8000) for client access

### Example .env for Node 0

```bash
VLLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
VLLM_DATA_PARALLEL_SIZE=2
VLLM_DATA_PARALLEL_RANK=0
VLLM_DATA_PARALLEL_ADDRESS=10.0.0.1  # This node's IP
VLLM_DATA_PARALLEL_RPC_PORT=13345
```

### Example .env for Node 1

```bash
VLLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
VLLM_DATA_PARALLEL_SIZE=2
VLLM_DATA_PARALLEL_RANK=1
VLLM_DATA_PARALLEL_ADDRESS=10.0.0.1  # Node 0's IP
VLLM_DATA_PARALLEL_RPC_PORT=13345
```

## Commands

```bash
# Build image
./deploy.sh build

# Start service
./deploy.sh up

# Stop service
./deploy.sh down

# View logs
./deploy.sh logs

# Check status
./deploy.sh status

# Restart service
./deploy.sh restart

# Full cleanup
./deploy.sh clean
```

Or use `docker compose` directly:

```bash
docker compose build
docker compose up -d
docker compose logs -f
docker compose down
```

## Troubleshooting

### Service won't start
1. Check logs: `./deploy.sh logs`
2. Verify GPU is available: `nvidia-smi`
3. Check network connectivity between nodes

### Nodes can't communicate
1. Verify firewall allows RPC port (13345)
2. Check `VLLM_DATA_PARALLEL_ADDRESS` is correct
3. Both nodes must use the same `VLLM_DATA_PARALLEL_SIZE`

### Out of memory
1. Reduce `VLLM_GPU_MEMORY_UTILIZATION` (default 0.9)
2. Reduce `VLLM_MAX_MODEL_LEN` (default 4096)
3. Reduce `VLLM_MAX_NUM_SEQS` (default 256)

## Production Checklist

- [ ] Copy appropriate .env file
- [ ] Set correct `VLLM_DATA_PARALLEL_ADDRESS`
- [ ] Set secure `VLLM_API_KEY`
- [ ] Open firewall ports (8000, 13345)
- [ ] Verify GPU drivers installed
- [ ] Run `./deploy.sh build`
- [ ] Run `./deploy.sh up`
- [ ] Verify health check passes
