#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-help}" in
  # --- Infrastructure ---
  up)
    info "Starting PostgreSQL and pgAdmin..."
    docker compose up -d
    ;;
  down)
    info "Stopping services..."
    docker compose down
    ;;
  down-v)
    warn "Stopping services and removing volumes..."
    docker compose down -v
    ;;

  # --- Backend ---
  backend-setup)
    info "Setting up backend..."
    cd "$SCRIPT_DIR/backend"
    uv sync
    info "Backend dependencies installed."
    ;;
  dev)
    info "Starting backend dev server..."
    cd "$SCRIPT_DIR/backend"
    uv run fastapi dev main.py --port 8000
    ;;
  lint)
    info "Linting backend..."
    cd "$SCRIPT_DIR/backend"
    uv run ruff check .
    ;;
  format)
    info "Formatting backend..."
    cd "$SCRIPT_DIR/backend"
    uv run ruff format .
    ;;
  test)
    info "Running backend tests..."
    cd "$SCRIPT_DIR/backend"
    uv run pytest "${@:2}"
    ;;

  # --- Database ---
  db-migrate)
    info "Creating new migration..."
    cd "$SCRIPT_DIR/backend"
    uv run alembic revision --autogenerate -m "${2:?Migration message required}"
    ;;
  db-upgrade)
    info "Running migrations..."
    cd "$SCRIPT_DIR/backend"
    uv run alembic upgrade head
    ;;
  db-downgrade)
    info "Rolling back last migration..."
    cd "$SCRIPT_DIR/backend"
    uv run alembic downgrade -1
    ;;
  db-history)
    info "Migration history:"
    cd "$SCRIPT_DIR/backend"
    uv run alembic history --verbose
    ;;

  # --- Frontend ---
  frontend-setup)
    info "Setting up frontend..."
    cd "$SCRIPT_DIR/frontend"
    pnpm install
    info "Frontend dependencies installed."
    ;;
  frontend-dev)
    info "Starting frontend dev server..."
    cd "$SCRIPT_DIR/frontend"
    pnpm dev
    ;;
  frontend-build)
    info "Building frontend..."
    cd "$SCRIPT_DIR/frontend"
    pnpm build
    ;;
  frontend-lint)
    info "Linting frontend..."
    cd "$SCRIPT_DIR/frontend"
    pnpm lint
    ;;

  # --- Full Stack ---
  setup)
    info "Full project setup..."
    "$0" up
    "$0" backend-setup
    "$0" frontend-setup
    info "Setup complete! Run './run.sh dev' and './run.sh frontend-dev' in separate terminals."
    ;;

  help|*)
    echo ""
    echo "POMS Development CLI"
    echo "===================="
    echo ""
    echo "Infrastructure:"
    echo "  up              Start PostgreSQL and pgAdmin"
    echo "  down            Stop services"
    echo "  down-v          Stop services and remove volumes"
    echo ""
    echo "Backend:"
    echo "  backend-setup   Install Python dependencies"
    echo "  dev             Start backend dev server (port 8000)"
    echo "  lint            Run Ruff linter"
    echo "  format          Run Ruff formatter"
    echo "  test [args]     Run pytest (pass extra args)"
    echo ""
    echo "Database:"
    echo "  db-migrate MSG  Create new Alembic migration"
    echo "  db-upgrade      Run all pending migrations"
    echo "  db-downgrade    Roll back last migration"
    echo "  db-history      Show migration history"
    echo ""
    echo "Frontend:"
    echo "  frontend-setup  Install frontend dependencies"
    echo "  frontend-dev    Start frontend dev server (port 3000)"
    echo "  frontend-build  Build frontend for production"
    echo "  frontend-lint   Run ESLint"
    echo ""
    echo "Full Stack:"
    echo "  setup           Run full project setup"
    echo ""
    ;;
esac
