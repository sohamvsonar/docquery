#!/usr/bin/env bash
# DocQuery - Build and Push Docker Images to ECR
# Usage: AWS_ACCOUNT_ID=123456789 AWS_REGION=us-east-1 ./build_and_push.sh

set -euo pipefail

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?ERROR: Set AWS_ACCOUNT_ID environment variable}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
BACKEND_REPO="docquery-backend"
WORKER_REPO="docquery-worker"
FRONTEND_REPO="docquery-frontend"

echo "============================================"
echo "DocQuery - Build & Push to ECR"
echo "============================================"
echo "AWS Region: $AWS_REGION"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Image Tag: $IMAGE_TAG"
echo "============================================"

# Login to ECR
echo "→ Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ECR_REGISTRY"

# Build Backend Image
echo ""
echo "→ Building backend image..."
docker build \
    -t "${BACKEND_REPO}:${IMAGE_TAG}" \
    -t "${BACKEND_REPO}:latest" \
    -f backend/Dockerfile \
    backend

# Tag and Push Backend
echo "→ Pushing backend image..."
docker tag "${BACKEND_REPO}:${IMAGE_TAG}" "${ECR_REGISTRY}/${BACKEND_REPO}:${IMAGE_TAG}"
docker tag "${BACKEND_REPO}:latest" "${ECR_REGISTRY}/${BACKEND_REPO}:latest"
docker push "${ECR_REGISTRY}/${BACKEND_REPO}:${IMAGE_TAG}"
docker push "${ECR_REGISTRY}/${BACKEND_REPO}:latest"

# Tag and Push Worker (reuses backend image)
echo ""
echo "→ Tagging worker image (reuses backend)..."
docker tag "${BACKEND_REPO}:${IMAGE_TAG}" "${ECR_REGISTRY}/${WORKER_REPO}:${IMAGE_TAG}"
docker tag "${BACKEND_REPO}:latest" "${ECR_REGISTRY}/${WORKER_REPO}:latest"
docker push "${ECR_REGISTRY}/${WORKER_REPO}:${IMAGE_TAG}"
docker push "${ECR_REGISTRY}/${WORKER_REPO}:latest"

# Build Frontend Image
echo ""
echo "→ Building frontend image..."
docker build \
    -t "${FRONTEND_REPO}:${IMAGE_TAG}" \
    -t "${FRONTEND_REPO}:latest" \
    -f frontend/Dockerfile \
    frontend

# Tag and Push Frontend
echo "→ Pushing frontend image..."
docker tag "${FRONTEND_REPO}:${IMAGE_TAG}" "${ECR_REGISTRY}/${FRONTEND_REPO}:${IMAGE_TAG}"
docker tag "${FRONTEND_REPO}:latest" "${ECR_REGISTRY}/${FRONTEND_REPO}:latest"
docker push "${ECR_REGISTRY}/${FRONTEND_REPO}:${IMAGE_TAG}"
docker push "${ECR_REGISTRY}/${FRONTEND_REPO}:latest"

echo ""
echo "============================================"
echo "✓ All images pushed successfully!"
echo "============================================"
echo "Backend: ${ECR_REGISTRY}/${BACKEND_REPO}:${IMAGE_TAG}"
echo "Worker:  ${ECR_REGISTRY}/${WORKER_REPO}:${IMAGE_TAG}"
echo "Frontend: ${ECR_REGISTRY}/${FRONTEND_REPO}:${IMAGE_TAG}"
echo "============================================"
