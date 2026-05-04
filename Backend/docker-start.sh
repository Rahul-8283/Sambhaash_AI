#!/bin/bash

# Docker Quick Start Script - Sambhaash AI Backend
# Usage: bash docker-start.sh

set -e

echo "🐳 Sambhaash AI - Docker Setup"
echo "=============================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop:"
    echo "   https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✅ Docker found: $(docker --version)"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found."
    exit 1
fi

echo "✅ docker-compose found: $(docker-compose --version)"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Using .env.docker as template..."
    cp .env.docker .env
    echo "✅ Created .env from .env.docker"
    echo "   ⚠️  Update .env with your actual API keys!"
fi

# Build images
echo ""
echo "🔨 Building Docker images..."
docker-compose build

# Start services
echo ""
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Verify services
echo ""
echo "📊 Service Status:"
docker-compose ps

# Health check
echo ""
echo "🏥 Health Checks:"

# Check Redis
if docker-compose exec redis redis-cli ping &> /dev/null; then
    echo "✅ Redis: Healthy"
else
    echo "⚠️  Redis: Checking..."
fi

# Check API
if curl -s http://localhost:8000/health &> /dev/null; then
    echo "✅ FastAPI: Healthy"
else
    echo "⚠️  FastAPI: Still starting... (wait 10 seconds)"
fi

echo ""
echo "=============================="
echo "✅ Docker Setup Complete!"
echo "=============================="
echo ""
echo "📚 Next Steps:"
echo "  1. Open API Docs:  http://localhost:8000/docs"
echo "  2. View logs:      docker-compose logs -f"
echo "  3. Stop services:  docker-compose down"
echo ""
echo "📖 For more info, see DOCKER_SETUP_GUIDE.md"
