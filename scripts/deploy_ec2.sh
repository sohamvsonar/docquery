#!/usr/bin/env bash
# DocQuery - EC2 Deployment Script
# Usage: ./deploy_ec2.sh <EC2_PUBLIC_IP>

set -euo pipefail

EC2_IP="${1:?ERROR: Provide EC2 public IP as first argument}"
SSH_KEY="${SSH_KEY:-~/.ssh/docquery-key.pem}"
EC2_USER="${EC2_USER:-ubuntu}"

echo "============================================"
echo "DocQuery - EC2 Deployment"
echo "============================================"
echo "Target: $EC2_USER@$EC2_IP"
echo "SSH Key: $SSH_KEY"
echo "============================================"

# Test SSH connection
echo "→ Testing SSH connection..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "echo 'SSH connection successful'"

# Copy repository files
echo ""
echo "→ Copying repository files..."
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' \
    -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    ./ "$EC2_USER@$EC2_IP:~/docquery/"

# Run remote setup
echo ""
echo "→ Running remote setup..."
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << 'ENDSSH'
set -e

cd ~/docquery

# Pull latest changes
if [ -d .git ]; then
    git pull origin main || true
fi

# Stop existing services
echo "Stopping existing services..."
docker-compose down || true

# Build and start services
echo "Building and starting services..."
docker-compose up -d --build

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check service status
docker-compose ps

# Run database initialization
echo "Initializing database..."
docker-compose exec -T backend python scripts/init_db.py || true

echo ""
echo "============================================"
echo "✓ Deployment complete!"
echo "============================================"
ENDSSH

# Test health endpoint
echo ""
echo "→ Testing health endpoint..."
sleep 5
curl -f "http://$EC2_IP:8000/health" && echo "" || echo "WARNING: Health check failed"

echo ""
echo "============================================"
echo "✓ EC2 Deployment Complete!"
echo "============================================"
echo "Backend API: http://$EC2_IP:8000"
echo "Frontend: http://$EC2_IP:3000"
echo "API Docs: http://$EC2_IP:8000/docs"
echo "============================================"
