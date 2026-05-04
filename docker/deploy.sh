#!/bin/bash
# ===========================================
# vLLM Service Deployment Script
# ===========================================
# 
# Usage:
#   ./deploy.sh              # Show help
#   ./deploy.sh build        # Build Docker image
#   ./deploy.sh up           # Start service
#   ./deploy.sh down         # Stop service
#   ./deploy.sh logs         # View logs
#   ./deploy.sh status       # Check status
#
# Prerequisites:
#   1. Copy .env.node0 or .env.node1 to .env
#   2. Edit .env with your configuration
#   3. Run ./deploy.sh up
# ===========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$SCRIPT_DIR"
CONFIG_DIR="$PROJECT_ROOT/src/vllm_service/config"
ENV_FILE="$CONFIG_DIR/.env"

# Parse --dev flag
DEV_MODE=0
ARGS=()
for arg in "$@"; do
    if [ "$arg" = "--dev" ]; then
        DEV_MODE=1
    else
        ARGS+=("$arg")
    fi
done
set -- "${ARGS[@]}"

COMPOSE_CMD="docker compose"
if [ "$DEV_MODE" = "1" ]; then
    COMPOSE_CMD="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
fi

# Change to docker directory
cd "$DOCKER_DIR"

print_banner() {
    echo -e "${BLUE}"
    echo "==========================================="
    echo "     vLLM Service Deployment Script"
    echo "==========================================="
    echo -e "${NC}"
}

print_help() {
    print_banner
    echo "Usage: $0 <command> [--dev]"
    echo ""
    echo "Commands:"
    echo "  build     Build Docker image"
    echo "  up        Start service (docker-compose up -d)"
    echo "  down      Stop service (docker-compose down)"
    echo "  logs      View logs (docker-compose logs -f)"
    echo "  status    Check service status"
    echo "  ps        List containers"
    echo "  restart   Restart service"
    echo "  clean     Remove containers, volumes, and images"
    echo ""
    echo "Flags:"
    echo "  --dev     Mount local src/ into container for hot reload (dev only)"
    echo ""
    echo "Setup:"
    echo "  1. Copy environment file:"
    echo "     cp src/vllm_service/config/.env.node0 src/vllm_service/config/.env  # For coordinator node"
    echo "     cp src/vllm_service/config/.env.node1 src/vllm_service/config/.env  # For worker node"
    echo ""
    echo "  2. Edit .env with your configuration"
    echo ""
    echo "  3. Deploy:"
    echo "     $0 build && $0 up"
    echo ""
}

check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: .env file not found!${NC}"
        echo ""
        echo "Please copy one of the example files:"
        echo "  cp src/vllm_service/config/.env.node0 src/vllm_service/config/.env  # For coordinator node (rank 0)"
        echo "  cp src/vllm_service/config/.env.node1 src/vllm_service/config/.env  # For worker node (rank 1)"
        echo ""
        echo "Then edit .env with your configuration."
        exit 1
    fi
    
    # Check required variables
    source "$ENV_FILE"
    
    if [ -z "$VLLM_DATA_PARALLEL_ADDRESS" ]; then
        echo -e "${RED}Error: VLLM_DATA_PARALLEL_ADDRESS not set in .env${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Configuration loaded:${NC}"
    echo "  Model: ${VLLM_MODEL_NAME}"
    echo "  DP Size: ${VLLM_DATA_PARALLEL_SIZE}"
    echo "  DP Rank: ${VLLM_DATA_PARALLEL_RANK}"
    echo "  Coordinator: ${VLLM_DATA_PARALLEL_ADDRESS}:${VLLM_DATA_PARALLEL_RPC_PORT}"
    echo ""
}

build() {
    print_banner
    echo -e "${YELLOW}Building Docker image...${NC}"
    $COMPOSE_CMD build
    echo -e "${GREEN}Build complete!${NC}"
}

up() {
    print_banner
    check_env
    
    echo -e "${YELLOW}Starting vLLM service...${NC}"
    
    if [ "$VLLM_DATA_PARALLEL_RANK" = "0" ]; then
        echo -e "${BLUE}Starting as Coordinator (rank 0)${NC}"
    else
        echo -e "${BLUE}Starting as Worker (rank ${VLLM_DATA_PARALLEL_RANK})${NC}"
    fi
    
    $COMPOSE_CMD up -d
    
    echo ""
    echo -e "${GREEN}Service started!${NC}"
    echo ""
    echo "Check status:"
    echo "  $0 status"
    echo ""
    echo "View logs:"
    echo "  $0 logs"
    echo ""
    echo "Test API:"
    echo "  curl http://localhost:${VLLM_PORT:-8000}/health"
}

down() {
    print_banner
    echo -e "${YELLOW}Stopping vLLM service...${NC}"
    $COMPOSE_CMD down
    echo -e "${GREEN}Service stopped.${NC}"
}

logs() {
    $COMPOSE_CMD logs -f
}

status() {
    print_banner
    echo -e "${YELLOW}Service Status:${NC}"
    echo ""
    $COMPOSE_CMD ps
    echo ""
    
    # Try to check health endpoint
    source "$ENV_FILE" 2>/dev/null || true
    PORT=${VLLM_PORT:-8000}
    
    if curl -s --connect-timeout 2 "http://localhost:${PORT}/health" > /dev/null 2>&1; then
        echo -e "${GREEN}Health check: OK${NC}"
    else
        echo -e "${RED}Health check: FAILED (service may still be starting)${NC}"
    fi
}

ps() {
    $COMPOSE_CMD ps
}

restart() {
    down
    echo ""
    up
}

clean() {
    print_banner
    echo -e "${RED}Warning: This will remove all containers, volumes, and images!${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $COMPOSE_CMD down -v --rmi local
        echo -e "${GREEN}Cleanup complete.${NC}"
    else
        echo "Cancelled."
    fi
}

# Main
case "${1:-}" in
    build)
        build
        ;;
    up)
        up
        ;;
    down)
        down
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    ps)
        ps
        ;;
    restart)
        restart
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        print_help
        exit 1
        ;;
esac

