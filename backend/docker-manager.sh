#!/bin/bash

# Docker Management Script for SMMS Backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Functions
build_dev() {
    print_status "Building development Docker images..."
    docker-compose build
}

build_prod() {
    print_status "Building production Docker images..."
    docker-compose -f docker-compose.prod.yml build
}

start_dev() {
    print_status "Starting development environment..."
    docker-compose up -d
    print_status "Development environment started!"
    print_status "Backend: http://localhost:8000"
    print_status "Database: localhost:5432"
    print_status "Redis: localhost:6379"
}

start_prod() {
    print_status "Starting production environment..."
    docker-compose -f docker-compose.prod.yml up -d
    print_status "Production environment started!"
}

stop_dev() {
    print_status "Stopping development environment..."
    docker-compose down
}

stop_prod() {
    print_status "Stopping production environment..."
    docker-compose -f docker-compose.prod.yml down
}

logs_dev() {
    docker-compose logs -f
}

logs_prod() {
    docker-compose -f docker-compose.prod.yml logs -f
}

shell() {
    print_status "Opening Django shell in container..."
    docker-compose exec backend python manage.py shell
}

migrate() {
    print_status "Running database migrations..."
    docker-compose exec backend python manage.py migrate
}

makemigrations() {
    print_status "Creating database migrations..."
    docker-compose exec backend python manage.py makemigrations
}

collectstatic() {
    print_status "Collecting static files..."
    docker-compose exec backend python manage.py collectstatic --noinput
}

createsuperuser() {
    print_status "Creating superuser..."
    docker-compose exec backend python manage.py createsuperuser
}

test() {
    print_status "Running tests..."
    docker-compose exec backend python manage.py test
}

cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v
    docker system prune -f
    print_status "Cleanup completed!"
}

reset() {
    print_warning "This will remove all containers, volumes, and data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Resetting environment..."
        docker-compose down -v
        docker-compose up -d
        sleep 10
        docker-compose exec backend python manage.py migrate
        print_status "Environment reset completed!"
    else
        print_status "Reset cancelled."
    fi
}

# Main script
case "$1" in
    build)
        build_dev
        ;;
    build-prod)
        build_prod
        ;;
    start|up)
        start_dev
        ;;
    start-prod|up-prod)
        start_prod
        ;;
    stop|down)
        stop_dev
        ;;
    stop-prod|down-prod)
        stop_prod
        ;;
    logs)
        logs_dev
        ;;
    logs-prod)
        logs_prod
        ;;
    shell)
        shell
        ;;
    migrate)
        migrate
        ;;
    makemigrations)
        makemigrations
        ;;
    collectstatic)
        collectstatic
        ;;
    createsuperuser)
        createsuperuser
        ;;
    test)
        test
        ;;
    cleanup)
        cleanup
        ;;
    reset)
        reset
        ;;
    *)
        echo "Usage: $0 {build|build-prod|start|start-prod|stop|stop-prod|logs|logs-prod|shell|migrate|makemigrations|collectstatic|createsuperuser|test|cleanup|reset}"
        echo ""
        echo "Development Commands:"
        echo "  build         - Build development images"
        echo "  start/up      - Start development environment"
        echo "  stop/down     - Stop development environment"
        echo "  logs          - View development logs"
        echo ""
        echo "Production Commands:"
        echo "  build-prod    - Build production images"
        echo "  start-prod    - Start production environment"
        echo "  stop-prod     - Stop production environment"
        echo "  logs-prod     - View production logs"
        echo ""
        echo "Management Commands:"
        echo "  shell         - Open Django shell"
        echo "  migrate       - Run database migrations"
        echo "  makemigrations- Create new migrations"
        echo "  collectstatic - Collect static files"
        echo "  createsuperuser - Create Django superuser"
        echo "  test          - Run tests"
        echo "  cleanup       - Clean up Docker resources"
        echo "  reset         - Reset entire environment (WARNING: deletes data)"
        exit 1
        ;;
esac
