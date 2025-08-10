#!/bin/bash

# University Chat Scraper - Docker Setup Script

set -e

DOCKER_DIR="$(dirname "$0")"
cd "$DOCKER_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_green() {
    echo -e "${GREEN}$1${NC}"
}

print_yellow() {
    echo -e "${YELLOW}$1${NC}"
}

print_red() {
    echo -e "${RED}$1${NC}"
}

# Function to start services
start_services() {
    print_green "🚀 Starting University Chat Scraper services..."
    
    print_yellow "Starting database services (PostgreSQL, Redis, Elasticsearch)..."
    docker-compose up -d postgres redis elasticsearch
    
    print_yellow "Waiting for databases to be ready..."
    sleep 10
    
    print_yellow "Starting backend service..."
    docker-compose up -d backend
    
    print_green "✅ All services started successfully!"
    print_yellow "🌐 Backend API available at: http://localhost:8000"
    print_yellow "📚 API Documentation at: http://localhost:8000/docs"
    print_yellow "🗄️  PostgreSQL: localhost:5432 (user: postgres, password: password, db: university_chat)"
    print_yellow "📦 Redis: localhost:6379"
    print_yellow "🔍 Elasticsearch: localhost:9200"
}

# Function to stop services
stop_services() {
    print_yellow "🛑 Stopping University Chat Scraper services..."
    docker-compose down
    print_green "✅ All services stopped!"
}

# Function to restart services
restart_services() {
    print_yellow "🔄 Restarting University Chat Scraper services..."
    stop_services
    start_services
}

# Function to show logs
show_logs() {
    if [ -z "$2" ]; then
        print_yellow "📋 Showing logs for all services..."
        docker-compose logs -f
    else
        print_yellow "📋 Showing logs for $2..."
        docker-compose logs -f "$2"
    fi
}

# Function to show status
show_status() {
    print_yellow "📊 Service Status:"
    docker-compose ps
    echo
    print_yellow "🔍 Quick Health Checks:"
    
    # Check backend
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_green "✅ Backend API is running"
    else
        print_red "❌ Backend API is not responding"
    fi
    
    # Check PostgreSQL
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_green "✅ PostgreSQL is ready"
    else
        print_red "❌ PostgreSQL is not ready"
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_green "✅ Redis is responding"
    else
        print_red "❌ Redis is not responding"
    fi
    
    # Check Elasticsearch
    if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        print_green "✅ Elasticsearch is running"
    else
        print_red "❌ Elasticsearch is not responding"
    fi
}

# Function to clean up (remove volumes)
cleanup() {
    print_yellow "🧹 Cleaning up all data (this will remove all databases)..."
    read -p "Are you sure? This will delete all data! (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        print_green "✅ Cleanup complete!"
    else
        print_yellow "Cleanup cancelled."
    fi
}

# Function to connect to database
connect_db() {
    print_yellow "🗄️  Connecting to PostgreSQL database..."
    docker-compose exec postgres psql -U postgres -d university_chat
}

# Show usage
usage() {
    echo "University Chat Scraper - Docker Management Script"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|logs|cleanup|db|help} [service]"
    echo ""
    echo "Commands:"
    echo "  start     - Start all services"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  status    - Show service status and health"
    echo "  logs      - Show logs (optionally for specific service)"
    echo "  cleanup   - Stop services and remove all data"
    echo "  db        - Connect to PostgreSQL database"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs backend"
    echo "  $0 status"
}

# Main script logic
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$@"
        ;;
    cleanup)
        cleanup
        ;;
    db)
        connect_db
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        if [ -z "$1" ]; then
            usage
        else
            print_red "Unknown command: $1"
            echo ""
            usage
        fi
        exit 1
        ;;
esac
