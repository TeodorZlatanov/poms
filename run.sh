#!/usr/bin/env bash
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() {
  echo -e "${RED}[ERROR]${NC} $1"
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require_docker() {
  if ! command -v docker &>/dev/null; then
    error "Docker is not installed. Please install Docker: https://docs.docker.com/get-docker/"
  fi
  if ! docker info &>/dev/null; then
    error "Docker is not running. Please start Docker and try again."
  fi
}

require_uv() {
  if ! command -v uv &>/dev/null; then
    error "uv is not installed. Please install it: https://docs.astral.sh/uv/getting-started/installation/"
  fi
}

require_node() {
  if ! command -v node &>/dev/null; then
    error "Node.js is not installed. Please install Node.js 20+: https://nodejs.org/"
  fi
}

require_pnpm() {
  require_node
  if ! command -v pnpm &>/dev/null; then
    error "pnpm is not installed. Please install it: npm install -g pnpm"
  fi
}

case "${1:-help}" in
# --- Infrastructure ---
up)
  require_docker
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
  require_uv
  info "Setting up backend..."
  cd "$SCRIPT_DIR/backend"
  uv sync
  info "Backend dependencies installed."
  ;;
dev)
  require_uv
  require_pnpm
  info "Starting backend (port 8000) and frontend (port 3000)..."
  cd "$SCRIPT_DIR/backend" && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!
  cd "$SCRIPT_DIR/frontend" && pnpm dev &
  FRONTEND_PID=$!
  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM
  info "Backend: http://localhost:8000  |  Frontend: http://localhost:3000"
  wait
  ;;
backend-dev)
  require_uv
  info "Starting backend dev server..."
  cd "$SCRIPT_DIR/backend"
  uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ;;
lint)
  require_uv
  info "Linting backend..."
  cd "$SCRIPT_DIR/backend"
  uv run ruff check .
  ;;
format)
  require_uv
  info "Formatting backend..."
  cd "$SCRIPT_DIR/backend"
  uv run ruff format .
  ;;
test)
  require_uv
  info "Running backend tests..."
  cd "$SCRIPT_DIR/backend"
  uv run pytest "${@:2}"
  ;;

# --- Database ---
db-migrate)
  require_uv
  info "Creating new migration..."
  cd "$SCRIPT_DIR/backend"
  uv run alembic revision --autogenerate -m "${2:?Migration message required}"
  ;;
db-upgrade)
  require_uv
  info "Running migrations..."
  cd "$SCRIPT_DIR/backend"
  uv run alembic upgrade head
  ;;
db-downgrade)
  require_uv
  info "Rolling back last migration..."
  cd "$SCRIPT_DIR/backend"
  uv run alembic downgrade -1
  ;;
db-history)
  require_uv
  info "Migration history:"
  cd "$SCRIPT_DIR/backend"
  uv run alembic history --verbose
  ;;
kb-seed)
  require_uv
  info "Seeding reference data (vendors, catalog, policies) into PostgreSQL..."
  cd "$SCRIPT_DIR/backend"
  uv run python -m scripts.seed_reference_data
  ;;
kb-ingest)
  require_uv
  info "Embedding knowledge base PDFs into LanceDB vector store..."
  cd "$SCRIPT_DIR/backend"
  uv run python -m scripts.ingest_knowledge "${@:2}"
  ;;
kb-init)
  info "Initializing knowledge base (seed reference data + embed PDFs)..."
  "$0" kb-seed
  "$0" kb-ingest
  info "Knowledge base ready."
  ;;

# --- Frontend ---
frontend-setup)
  require_pnpm
  info "Setting up frontend..."
  cd "$SCRIPT_DIR/frontend"
  pnpm install
  info "Frontend dependencies installed."
  ;;
frontend-dev)
  require_pnpm
  info "Starting frontend dev server..."
  cd "$SCRIPT_DIR/frontend"
  pnpm dev
  ;;
frontend-build)
  require_pnpm
  info "Building frontend..."
  cd "$SCRIPT_DIR/frontend"
  pnpm build
  ;;
frontend-lint)
  require_pnpm
  info "Linting frontend..."
  cd "$SCRIPT_DIR/frontend"
  pnpm lint
  ;;
frontend-check)
  require_pnpm
  info "Running frontend type check, lint, and build..."
  cd "$SCRIPT_DIR/frontend"
  npx tsc --noEmit && pnpm lint && pnpm build
  info "Frontend checks passed."
  ;;

# --- Full Stack ---
setup)
  require_docker
  require_uv
  require_pnpm
  info "Full project setup..."
  if [ ! -f "$SCRIPT_DIR/.env" ]; then
    warn "Creating .env from template — edit it with your API keys."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  fi
  "$0" up
  "$0" backend-setup
  "$0" frontend-setup
  echo ""
  info "Setup complete! Next steps:"
  echo ""
  echo "  1. Edit .env with your Azure OpenAI API keys and (optionally) Gmail credentials"
  echo "  2. Run './run.sh kb-init' to seed reference data and embed the RAG knowledge base"
  echo "  3. Run './run.sh dev' to start the backend and frontend dev servers"
  echo ""
  echo "  The app will be available at http://localhost:3000"
  echo ""
  ;;
check)
  info "Running all checks..."
  "$0" frontend-check
  "$0" lint
  "$0" test
  info "All checks passed."
  ;;

help | *)
  echo ""
  echo "POMS Development CLI"
  echo "===================="
  echo ""
  echo "Infrastructure:"
  echo "  up              Start PostgreSQL"
  echo "  down            Stop services"
  echo "  down-v          Stop services and remove volumes"
  echo ""
  echo "Backend:"
  echo "  backend-setup   Install Python dependencies"
  echo "  dev             Start backend + frontend together"
  echo "  backend-dev     Start backend dev server only (port 8000)"
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
  echo "Knowledge Base:"
  echo "  kb-seed         Seed reference data (vendors, catalog, policies)"
  echo "  kb-ingest       Embed knowledge PDFs into LanceDB"
  echo "  kb-init         Run seed + ingest together"
  echo ""
  echo "Frontend:"
  echo "  frontend-setup  Install frontend dependencies"
  echo "  frontend-dev    Start frontend dev server (port 3000)"
  echo "  frontend-build  Build frontend for production"
  echo "  frontend-lint   Run ESLint"
  echo "  frontend-check  Run tsc + lint + build"
  echo ""
  echo "Full Stack:"
  echo "  setup           Run full project setup (DB + deps + .env)"
  echo "  check           Run all checks (frontend + backend lint + tests)"
  echo ""
  ;;
esac
